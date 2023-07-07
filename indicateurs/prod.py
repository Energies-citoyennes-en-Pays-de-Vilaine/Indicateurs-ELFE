import asyncio
from connectionBDDProd import *
from connectionZabbix import *
import pandas as pd
import os
from calcul import *
from pandasql import sqldf
import sqlalchemy
from pyzabbix import ZabbixAPI
from datetime import datetime
import time

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
            nb_app_lancés_24h = pd.read_sql("SELECT COUNT(DISTINCT machine_id) FROM result \
                                                        WHERE decisions_0 = 1\
                                                        AND first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)"
                                        , con = conn)     
        pourcentage_app_lancés_24h = (100*nb_app_lancés_24h)/nb_app_EMS
        pourcentage_app_lancés_24h = round(pourcentage_app_lancés_24h, 1)
        return pourcentage_app_lancés_24h
    
    #Calcul du cumul des kW d'énergie placés par l'EMS depuis le début du projet
    def cumul_enr() -> int:
        with conn_sortie.engine.connect() as conn:
            #On fabrique deux tables sous la forme machine_type | nombre de lancements
            #1e table pour les machines discoutinues : on compte chaque lancement
            coeffs_discontinu:pd.DataFrame = pd.read_sql("SELECT machine_type, COUNT(*) FROM result\
                                                WHERE decisions_0 = 1\
                                                AND machine_type IN (111, 112, 113, 221, 225, 515)\
                                            GROUP BY machine_type"
                                    , con = conn) #Compléter les machines_type
            #2e table pour les machines continues : si pas de arrêt / relance, on compte un lancement par jour
            coeffs_continu:pd.DataFrame = pd.read_sql("""SELECT * FROM 
                                                        (SELECT machine_type, COUNT(*) FROM 
                                                            (SELECT DISTINCT * FROM 
                                                                (SELECT first_valid_timestamp/86400 AS day, machine_id, machine_type FROM 
                                                                        result WHERE decisions_0 = 1) AS T1) AS T2
                                                                        GROUP BY machine_type) AS T3 WHERE machine_type IN (131, 151, 155, -1)"""
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
        
    #Calcul du pourcentage de la conso d'énergie des foyers placée
    def conso_enr_placee() -> int:
        #On commence par calculer la quantité d'énergie placée dans les dernières 24h
        with conn_sortie.engine.connect() as conn:
            #On fabrique deux tables sous la forme machine_type | nombre de lancements
            cumul_enr_placee_24h:pd.DataFrame = pd.read_sql(""" SELECT SUM((0.25)*(p_c_with_flexible_consumption.power - p_c_without_flexible_consumption.power)) FROM p_c_with_flexible_consumption
                                                        INNER JOIN p_c_without_flexible_consumption
                                                        USING(data_timestamp)
                                                        WHERE p_c_with_flexible_consumption.data_timestamp >= (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400) """
                            , con = conn)
            cumul_enr_placee_24h = -cumul_enr_placee_24h
        cumul_enr_placee_24h = int(cumul_enr_placee_24h.loc[0]['sum'])
        #Calcul de la consommation d'énergie du panel mis à l'échelle les dernières 24h (item Panel_R_puissance_mae dans Zabbix)
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 60 * 24)
        puissance_panel_mae = 0
        for i in zapi.history.get(hostids = [10084], itemids = [44968], time_from = tf, time_till = tt, output = "extend", limit = 1440, history = 0):
            puissance_panel_mae += int(float(i['value'])) * (1/60) #Panel_R_puissance_mae
        pourcentage_enr_conso_placee = int(100*(cumul_enr_placee_24h/puissance_panel_mae))
        return pourcentage_enr_conso_placee
    
    def cumul_enr_autoconso() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = 1667287596
        #Calcul de la production mise à l'échelle sur l'heure (en Wh)
        enr_prod_mae = 0
        for i in zapi.history.get(hostids = [10084], itemids = [44969], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            enr_prod_mae += int(float(i['value']))*(1/20) #Panel_Prod_puissance_mae : 1 valeur toutes les 3 min
        #Calcul de la production en surplus à partir de l'équilibre (en Wh)
        surplus_prod = 0
        for i in zapi.history.get(hostids = [10084], itemids = [42883], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            if (float(i['value'])>0):
                surplus_prod += int(float(i['value']))*(1/60) #equilibre_general_p_c : 1 valeur par minute
        #Calcul de l'enr produite et consommée sur le territoire
        cumul_autoconso = int(enr_prod_mae - surplus_prod)
        return cumul_autoconso
    
    def part_eolien_prod_15min() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 15)
        #Production totale d'enr sur le dernier 1/4h
        prod_enr = 0
        #Production d'éolien sur le dernier 1/4h
        puissance_eolien = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45198], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_solaire
        for i in zapi.history.get(hostids = [10084], itemids = [45248], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_methanisation
        for i in zapi.history.get(hostids = [10084], itemids = [45197], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_eolienne
            puissance_eolien += int(i['value'])
        #Calcul du pourcentage
        pourcentage_prod_eolien = 100*puissance_eolien/prod_enr
        return int(pourcentage_prod_eolien)
    
    def part_solaire_prod_15min() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 15)
        #Production totale d'enr sur le dernier 1/4h
        prod_enr = 0
        #Production de solaire sur le dernier 1/4h
        puissance_solaire = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45198], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_solaire
            puissance_solaire += int(i['value'])
        for i in zapi.history.get(hostids = [10084], itemids = [45248], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_methanisation
        for i in zapi.history.get(hostids = [10084], itemids = [45197], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_eolienne
        #Calcul du pourcentage
        pourcentage_prod_solaire = 100*puissance_solaire/prod_enr
        return int(pourcentage_prod_solaire)
    
    def part_metha_prod_15min() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 15)
        #Production totale d'enr sur le dernier 1/4h
        prod_enr = 0
        #Production de metha sur le dernier 1/4h
        puissance_metha = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45198], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_solaire
        for i in zapi.history.get(hostids = [10084], itemids = [45248], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_methanisation
            puissance_metha += int(i['value'])
        for i in zapi.history.get(hostids = [10084], itemids = [45197], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #Prod_eolienne
        #Calcul du pourcentage
        pourcentage_prod_metha = 100*puissance_metha/prod_enr
        return int(pourcentage_prod_metha)
    
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
    
    conso_ener_placee = [conso_enr_placee()]
    df_conso = pd.DataFrame(conso_ener_placee)
    res_conso = df_conso.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Pourcentage_energie_consommee_placee " + res_conso + "\n")
    
    part_eol = [part_eolien_prod_15min()]
    df_eol = pd.DataFrame(part_eol)
    res_eol = df_eol.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Part_eolien_prod " + res_eol + "\n")
    
    part_sol = [part_solaire_prod_15min()]
    df_sol = pd.DataFrame(part_sol)
    res_sol = df_sol.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Part_solaire_prod " + res_sol + "\n")
    
    part_meth = [part_metha_prod_15min()]
    df_meth = pd.DataFrame(part_meth)
    res_meth = df_meth.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Part_metha_prod " + res_meth + "\n")
        
    #Connection au Zabbix
    zab = ConnectionZabbix('192.168.30.111', 'Zabbix server')
    
    #Création et ajout des différentes mesures à l'attribut measurements de l'objet Zabbix
    m1 = zb.Measurement(zab.host, "Nombre_appareils_connectes", res1)
    zab.measurements.add_measurement(m1)
        
    m2 = zb.Measurement(zab.host, "Pourcentage_app_lances_24h", res2)
    zab.measurements.add_measurement(m2)
    
    m_cumul = zb.Measurement(zab.host, "Cumul_energie_placee", res_cumul)
    zab.measurements.add_measurement(m_cumul)
    
    m_conso = zb.Measurement(zab.host, "Pourcentage_energie_consommee_placee", res_conso)
    zab.measurements.add_measurement(m_conso)
    
    m_eol = zb.Measurement(zab.host, "Part_eolien_prod", res_eol)
    zab.measurements.add_measurement(m_eol)
    
    m_sol = zb.Measurement(zab.host, "Part_solaire_prod", res_sol)
    zab.measurements.add_measurement(m_sol)
    
    m_meth = zb.Measurement(zab.host, "Part_metha_prod", res_meth)
    zab.measurements.add_measurement(m_meth)

    #Envoi de toutes les mesures au Zabbix
    await zab.response()


if __name__ == "__main__":
    asyncio.run(main())