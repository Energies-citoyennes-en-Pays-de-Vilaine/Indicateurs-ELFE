import asyncio
from connectionBDDProd import *
from connectionZabbix import *
import pandas as pd
import os
from calcul import *
from pandasql import sqldf
import sqlalchemy

async def main():
    
    sortie = 'ems_sortie'
    coordo = 'bdd_coordination'
    
    #Connection aux BDDs
    conn_sortie = ConnectionBDDProd(sortie)
    conn_coordo = ConnectionBDDProd(coordo, "bdd_coordination_schema")

    #Connection aux tables dont on a besoin
    result = conn_sortie.get_table('result')
    conso = conn_coordo.get_table_with_schema('equipement_pilote_consommation_moyenne', 'bdd_coordination_schema')
    withflex = conn_sortie.get_table('p_c_with_flexible_consumption')
    withoutflex = conn_sortie.get_table('p_c_without_flexible_consumption')
    equipement_pilote_ou_mesure = conn_coordo.get_table_with_schema('equipement_pilote_ou_mesure', 'bdd_coordination_schema')
        
    #Calcul du nombre d'appareils connectés par 1/4h
    def indic_appareils_connectes() -> int : 
        with conn_sortie.engine.connect() as conn:
            appconn = pd.read_sql("SELECT COUNT(*) FROM result\
                                    GROUP BY first_valid_timestamp\
                                    ORDER BY first_valid_timestamp DESC\
                                    LIMIT 1"\
                                    , con = conn)
        return appconn
    
    #Calcul du pourcentage des appareils de ELFE lancés dans les dernières 24h
    # Actuellement, il est mis au niveau du pourcentage de machines activées dans Viriya
    #Rajouter des types dans la liste si de nouveaux types qu'on ne peut pas piloter s'ajoutent
    def pourcentage_app_lancés_24h() -> int :
        with conn_coordo.engine.connect() as conn:
            nb_app_EMS = pd.read_sql("SELECT COUNT(*) FROM equipement_pilote_ou_mesure\
                                        WHERE equipement_pilote_ou_mesure_type_id NOT IN (410, 901, 910, 920)"
                                    , con = conn)        
        with conn_sortie.engine.connect() as conn:
            nb_app_lancés_24h_continu = pd.read_sql("SELECT COUNT(DISTINCT machine_id) FROM result \
                                                        WHERE machine_type IN (131, 151, 155)\
                                                        AND decisions_0 = 1\
                                                        AND first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)"
                                        , con = conn)        
            nb_app_lancés_24h_discontinu = pd.read_sql("SELECT COUNT(*) FROM result AS r1 \
                                                        INNER JOIN  result AS r2 ON r1.machine_id = r2.machine_id\
                                                            WHERE r2.machine_type IN (221, 112, 111, 113, 225, 515)\
                                                            AND r2.first_valid_timestamp = r1.first_valid_timestamp + 900\
                                                            AND r2.decisions_0 = 0\
                                                            AND r1.decisions_0 = 1\
                                                            AND r2.first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)"
                                            , con = conn)
        nb_app_lancés_24h = nb_app_lancés_24h_continu + nb_app_lancés_24h_discontinu        
        pourcentage_app_lancés_24h = (100*nb_app_lancés_24h)/nb_app_EMS
        pourcentage_app_lancés_24h = round(pourcentage_app_lancés_24h, 1)
        return pourcentage_app_lancés_24h
    
    #Calcul du cumul de kW d'énergie placés par l'EMS depuis le début du projet
    def cumul_enr() -> int:
        with conn_sortie.engine.connect() as conn:
            #On fabrique deux tables sous la forme machine_type | nombre de lancements
            #1e table pour les machines discoutinues : on compte chaque lancement
            coeffs_discontinu:pd.DataFrame = pd.read_sql("SELECT machine_type, COUNT(*) FROM result\
                                                WHERE decisions_0 = 1\
                                                AND machine_type IN (111)\
                                            GROUP BY machine_type"
                                    , con = conn) #Compléter les machines_type
            #2e table pour les machines continues : si pas de arrêt / relance, on compte un lancement par jour
            coeffs_continu:pd.DataFrame = pd.read_sql("""SELECT * FROM 
                                                        (SELECT machine_type, COUNT(*) FROM 
                                                            (SELECT DISTINCT * FROM 
                                                                (SELECT first_valid_timestamp/86400 AS day, machine_id, machine_type FROM 
                                                                        result WHERE decisions_0 = 1) AS T1) AS T2
                                                                        GROUP BY machine_type) AS T3 WHERE machine_type IN (131)"""
                                    , con = conn) #Compléter les machines_type

            #On récupère la table machine_type | consommation moyenne.
            with conn_coordo.engine.connect() as conn:
                conso_energie:pd.DataFrame = pd.read_sql("SELECT equipement_pilote_type_id, consommation FROM equipement_pilote_consommation_moyenne"
                        , con = conn)
            #cumul_enr correspond à l'indicateur final qu'on initialise à 0
            cumul_enr = 0
            #On l'incrémente avec pour chaque ligne des tableaux continus et discontinus nb de machines d'un type * moyenne de l'énergie consommée par ce type de machine 
            for i in coeffs_discontinu.index:
                for j in conso_energie.index:
                    if coeffs_discontinu.loc[i]['machine_type'] == conso_energie.loc[j]['equipement_pilote_type_id']:
                        cumul_enr += coeffs_discontinu.loc[i]['count'] * conso_energie.loc[j]['consommation']
            for i in coeffs_continu.index:
                for j in conso_energie.index:
                    if coeffs_continu.loc[i]['machine_type'] == conso_energie.loc[j]['equipement_pilote_type_id']:
                        cumul_enr += coeffs_continu.loc[i]['count'] * conso_energie.loc[j]['consommation']
            return int(cumul_enr)
    
    #Encapsulation dans un csv
    #On récupère le path du fichier courant qu'on concatène avec le nom voulu du fichier csv
    path = os.path.dirname(__file__)
    filename = f"indics-prod.csv"
    finalpath = os.path.join(path, filename)
    #Puis on ouvre le fichier en écriture
    fichier = open(finalpath, "w")
    
    appconn = indic_appareils_connectes()
    df1 = pd.DataFrame(appconn)   
    res1 = df1.to_string (header=False, index = False)
    fichier.write("\"Zabbix server\" Nombre_appareils_connectes " + res1 + "\n")
    
    pourcentage_app = pourcentage_app_lancés_24h()
    df2 = pd.DataFrame(pourcentage_app)
    res2 = df2.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Pourcentage_app_lances_24h " + res2 + "\n")
    
    cumul_ener = [cumul_enr()]
    df_cumul = pd.DataFrame(cumul_ener)
    res_cumul = df_cumul.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Cumul_energie_placee " + res_cumul + "\n")
        
    #Connection au Zabbix
    zab = ConnectionZabbix('192.168.30.111', 'Zabbix server')
    
    #Création et ajout des différentes mesures à l'attribut measurements de l'objet Zabbix
    m1 = zb.Measurement(zab.host, "Nombre_appareils_connectes", res1)
    zab.measurements.add_measurement(m1)
        
    m2 = zb.Measurement(zab.host, "Pourcentage_app_lances_24h", res2)
    zab.measurements.add_measurement(m2)
    
    m_cumul = zb.Measurement(zab.host, "Cumul_energie_placee", res_cumul)
    zab.measurements.add_measurement(m_cumul)

    #Envoi de toutes les mesures au Zabbix
    await zab.response()


if __name__ == "__main__":
    asyncio.run(main())