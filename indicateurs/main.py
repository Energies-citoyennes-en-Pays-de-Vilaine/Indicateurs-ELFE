import asyncio
from connectionBDD import *
from connectionZabbix import *
from datetime import datetime
import time
import sys
import pandas as pd
import os
from calcul import *
from pandasql import sqldf
from pyzabbix import ZabbixAPI

#On récupère le path pour que le fichier exécutable soit créé dans le même répertoire
path = os.path.dirname(sys.executable)

#Pour mettre la date courante dans le nom du fichier csv crée avec un fstring
now = datetime.now()
nowstr = now.strftime("%d%m%Y")

#Enabling debug logging for the pyzabbix API
stream = logging.StreamHandler(sys.stdout)
stream.setLevel(logging.DEBUG)
log = logging.getLogger('pyzabbix')
log.addHandler(stream)
log.setLevel(logging.DEBUG)

async def main():
    
    sortie = 'preprod_sortie_ems'
    coordo = 'preprod_bdd_coordination'
    histo = 'preprod_historisation'
    
    #Connection aux 2 BDDs
    try:
        conn_sortie = ConnectionBDD(sortie)
        print(f"Connection to " +sortie+ " created successfully.")
    except Exception as ex:
        print("Connection to " +sortie+ " could not be made due to the following error: \n", ex)
        
    try:
        conn_coordo = ConnectionBDD(coordo, "bdd_coordination_schema")
        print(f"Connection to " +coordo+ " created successfully.")
    except Exception as ex:
        print("Connection to " +coordo+ " could not be made due to the following error: \n", ex)
        
    #Connection aux tables dont on a besoin
    try:
        result = conn_sortie.get_table('result')
        print(f"Table for result created successfully.")
    except Exception as ex:
        print("Table for result could not be made due to the following error: \n", ex)
        
    try:
        conso = conn_sortie.get_table('equipement_pilote_consommation_moyenne')
        print(f"Table for conso created successfully.")
        print(conso)
    except Exception as ex:
        print("Table for conso could not be made due to the following error: \n", ex)
        
    try:
        withflex = conn_sortie.get_table('p_c_with_flexible_consumption')
        print(f"Table for p_c_with_flexible_consumption created successfully.")
    except Exception as ex:
        print("Table for p_c_with_flexible_consumption could not be made due to the following error: \n", ex)
        
    try:
        withoutflex = conn_sortie.get_table('p_c_without_flexible_consumption')
        print(f"Table for p_c_without_flexible_consumption created successfully.")
    except Exception as ex:
        print("Table for p_c_without_flexible_consumption could not be made due to the following error: \n", ex)
        
    try:
        equipement_pilote_ou_mesure = conn_coordo.get_table_with_schema('equipement_pilote_ou_mesure', 'bdd_coordination_schema')
        print(f"Table for equipement_pilote_ou_mesure created successfully.")
    except Exception as ex:
        print("Table for equipement_pilote_ou_mesure could not be made due to the following error: \n", ex)
    
    try:
        equipement_mesure_compteur_electrique = conn_coordo.get_table_with_schema('equipement_mesure_compteur_electrique', 'bdd_coordination_schema')
        print(f"Table for equipement_mesure_compteur_electrique created successfully.")
    except Exception as ex:
        print("Table for equipement_mesure_compteur_electrique could not be made due to the following error: \n", ex)
    
        
    #Calcul du nombre d'appareils connectés par 1/4h
    def indic_appareils_connectes() -> int : 
        with conn_sortie.engine.connect() as conn:
            appconn = pd.read_sql("SELECT COUNT(*) FROM result\
                                    GROUP BY first_valid_timestamp\
                                    ORDER BY first_valid_timestamp DESC\
                                    LIMIT 1"\
                                    , con = conn)
        return appconn
        
    #Calcul du nombre d'appareils pilotés la semaine dernière
    def indic_appareils_pilotes_semaine() -> int :
        with conn_sortie.engine.connect() as conn:
            appsem = pd.read_sql("SELECT COUNT(DISTINCT machine_id) AS Nombre_appareils_pilotés_la_semaine_dernière FROM result\
                                    WHERE first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 604800)", con = conn)
        return appsem
    
    #Calcul du pourcentage des appareils de ELFE lancés dans les dernières 24h
    # Actuellement, il est mis au niveau du pourcentage de machines activées dans Viriya
    #Rajouter des types dans la liste si de nouveaux types qu'on ne peut pas piloter s'ajoutent
    def pourcentage_app_lancés_24h() -> int :
        with conn_coordo.engine.connect() as conn:
            nb_app_EMS = pd.read_sql("SELECT COUNT(*) FROM equipement_pilote_ou_mesure\
                                        WHERE equipement_pilote_ou_mesure_type_id NOT IN (410, 901, 910, 920)"
                                    , con = conn)
            print("Nb app EMS : ", nb_app_EMS)       
        with conn_sortie.engine.connect() as conn:
            nb_app_lancés_24h_continu = pd.read_sql("SELECT COUNT(DISTINCT machine_id) FROM result \
                                                        WHERE machine_type IN (131, -1)\
                                                        AND decisions_0 = 1\
                                                        AND first_valid_timestamp >= (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)"
                                        , con = conn) # Compléter les machine_type
            """
            nb_app_lancés_24h_discontinu = pd.read_sql("SELECT COUNT(*) FROM result AS r1 \
                                                        INNER JOIN  result AS r2 ON r1.machine_id = r2.machine_id\
                                                            WHERE r2.machine_type IN (221)\
                                                            AND r2.first_valid_timestamp = r1.first_valid_timestamp + 900\
                                                            AND r2.decisions_0 = 0\
                                                            AND r1.decisions_0 = 1\
                                                            AND r2.first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)"
                                            , con = conn) # Compléter les machine_type : 112, 111, 113, 225, 515
            """
            nb_app_lancés_24h_discontinu = pd.read_sql(""" SELECT COUNT(*) FROM result 
                                                WHERE decisions_0 = 1
                                                AND machine_type IN (221)
                                                AND first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)"""
                                        , con = conn)
        nb_app_lancés_24h = nb_app_lancés_24h_continu + nb_app_lancés_24h_discontinu
        pourcentage_app_lancés_24h = (100*nb_app_lancés_24h)/nb_app_EMS
        pourcentage_app_lancés_24h = round(pourcentage_app_lancés_24h, 1)
        return pourcentage_app_lancés_24h   
        #Liste continu à terme (en prod) : 131, 151, 155
        #Liste discontinu à terme (en prod) : 515, 112, 111, 113, 221, 225
    
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
            print("Coeffs discontinus : " , coeffs_discontinu)
            #2e table pour les machines continues : si pas de arrêt / relance, on compte un lancement par jour
            coeffs_continu:pd.DataFrame = pd.read_sql("""SELECT * FROM 
                                                        (SELECT machine_type, COUNT(*) FROM 
                                                            (SELECT DISTINCT * FROM 
                                                                (SELECT first_valid_timestamp/86400 AS day, machine_id, machine_type FROM 
                                                                        result WHERE decisions_0 = 1) AS T1) AS T2
                                                                        GROUP BY machine_type) AS T3 WHERE machine_type IN (131)"""
                                    , con = conn) #Compléter les machines_type
            print("Coeffs continus : ", coeffs_continu)

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
                
            
        """
        print("Conso énergie : ", conso_energie)
        print(conso_energie.columns)
        print(conso_energie.index)
        for i in conso_energie.index:
            print(conso_energie.loc[i]['consommation'])
        print(conso_energie['equipement_pilote_type_id'])
        print(coeffs_discontinu['machine_type'])
        """
        
        """
        testres = pd.DataFrame({'ts': [10, 15, 20, 10], 'machine_id': [1, 1, 1, 2], 'machine_type': [131, 131, 131, 131], 'decisions_0': [1, 1, 1, 1]})
        
        print("Table de départ : ", testres)
        
        Q1 = "SELECT ts/10 AS day, machine_id, machine_type FROM testres WHERE decisions_0 = 1"
        T1 = sqldf(Q1)
        print("Table 1 : ", T1)
        
        Q2 = f"SELECT DISTINCT * FROM ({Q1}) AS T1"
        T2 = sqldf(Q2)
        print("Table 2 : ", T2)
        
        Q3 = f"SELECT machine_type, COUNT(*) FROM ({Q2}) AS T2 GROUP BY machine_type"
        T3 = sqldf(Q3)
        print("Table 3 : ", T3)
        
        Q4 = f"SELECT * FROM ({Q3}) AS T3 WHERE machine_type IN (131)"
        T4 = sqldf(Q4)
        print("Table 4 : ", T4)
        """
        
        #Q = """SELECT * FROM 
         #           (SELECT machine_type, COUNT(*) FROM 
          #              (SELECT DISTINCT * FROM 
           #                 (SELECT ts/10 AS day, machine_id, machine_type FROM 
            #                    testres WHERE decisions_0 = 1) AS T1) AS T2
             #                   GROUP BY machine_type) AS T3 WHERE machine_type IN (131)"""
        #TF = sqldf(Q)
        #print("Table finale : ", TF)
                
        #query_finale = """ SELECT SUM(inter.days) FROM (SELECT machine_id, machine_type, COUNT(DISTINCT ts/10) AS days FROM testres
         #                               WHERE decisions_0 = 1
          #                              AND machine_type IN(131)
           #                         GROUP BY machine_id) AS inter
            #                GROUP BY inter.machine_type """

        #test_final = sqldf(query_finale)
        #print("TEST ULTIME : ", test_final)
        
        #coeffs_continu:pd.DataFrame = pd.read_sql(""" SELECT machine_type, machine_id, SUM(inter.days) FROM (SELECT machine_id, machine_type, COUNT(DISTINCT first_valid_timestamp/86400) AS days
         #                                                                               FROM result
          #                                                                              WHERE decisions_0 = 1
           #                                                                             AND machine_type IN(131)
            #                                                                            GROUP BY result.machine_id, result.machine_type) AS inter
             #                                           """
              #                      , con = conn) #Compléter les machines_type
        
        #table_interm:pd.DataFrame = pd.read_sql(""" SELECT machine_id, machine_type, COUNT(DISTINCT first_valid_timestamp/86400) AS days
         #                                                                               FROM result
          #                                                                              WHERE decisions_0 = 1
           #                                                                             AND machine_type IN(131)"""
            #                        , con = conn)
        #print("Table test : ", table_interm)
        
        #print("Coeffs continu : " , coeffs_continu)
        
        
        #query_inter:pd.DataFrame = pd.read_sql(""" SELECT t.machine_id, r.machine_type, t.days FROM 
        #                                            (SELECT machine_id, COUNT(DISTINCT first_valid_timestamp/86400) AS days FROM result
	     #                                           WHERE machine_type IN (131)
          #                                          AND decisions_0 = 1
           #                                         GROUP BY machine_id) t 
            #                                    JOIN result r ON r.machine_id = t.machine_id """
             #                       , con = conn)
        
        #query_inter_2:pd.DataFrame = pd.read_sql(""" SELECT machine_type, machine_id, COUNT(DISTINCT first_valid_timestamp/86400) AS days FROM result
	     #                                           WHERE machine_type IN (131)
          #                                          AND decisions_0 = 1
           #                                         """
            #                        , con = conn)
        #print("Table inter : ", query_inter_2)
    
    
    #Calcul du pourcentage de la conso d'énergie des foyers placée
    def conso_enr_placee() -> int:
        #On commence par calculer la quantité d'énergie placée dans les dernières 24h
        with conn_sortie.engine.connect() as conn:
                #On fabrique deux tables sous la forme machine_type | nombre de lancements
                #1e table pour les machines discoutinues : on compte chaque lancement
                coeffs_discontinu:pd.DataFrame = pd.read_sql("SELECT machine_type, COUNT(*) FROM result\
                                                    WHERE decisions_0 = 1\
                                                    AND machine_type IN (111)\
                                                    AND first_valid_timestamp >= (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)\
                                                GROUP BY machine_type"
                                        , con = conn) #Compléter les machines_type
                print("Coeffs discontinus : " , coeffs_discontinu)
                #2e table pour les machines continues : si pas de arrêt / relance, on compte un lancement pour les dernières 24h
                coeffs_continu:pd.DataFrame = pd.read_sql("""SELECT * FROM 
                                                            (SELECT machine_type, COUNT(*) FROM 
                                                                (SELECT DISTINCT * FROM 
                                                                    (SELECT machine_id, machine_type FROM result
                                                                            WHERE first_valid_timestamp >= (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)
                                                                            AND decisions_0 = 1) AS T1) AS T2
                                                                            GROUP BY machine_type) AS T3 WHERE machine_type IN (131)
                                                                            """
                                        , con = conn) #Compléter les machines_type
                print("Coeffs continus : ", coeffs_continu)

                #On récupère la table machine_type | consommation moyenne.
                with conn_coordo.engine.connect() as conn:
                    conso_energie:pd.DataFrame = pd.read_sql("SELECT equipement_pilote_type_id, consommation FROM equipement_pilote_consommation_moyenne"
                            , con = conn)
                #cumul_enr_24h correspond à l'indicateur final qu'on initialise à 0
                cumul_enr_24h = 0
                #On l'incrémente avec pour chaque ligne des tableaux continus et discontinus nb de machines d'un type * moyenne de l'énergie consommée par ce type de machine 
                for i in coeffs_discontinu.index:
                    for j in conso_energie.index:
                        if coeffs_discontinu.loc[i]['machine_type'] == conso_energie.loc[j]['equipement_pilote_type_id']:
                            cumul_enr_24h += coeffs_discontinu.loc[i]['count'] * conso_energie.loc[j]['consommation']
                for i in coeffs_continu.index:
                    for j in conso_energie.index:
                        if coeffs_continu.loc[i]['machine_type'] == conso_energie.loc[j]['equipement_pilote_type_id']:
                            cumul_enr_24h += coeffs_continu.loc[i]['count'] * conso_energie.loc[j]['consommation']
                print ("Enr placée 24h : ", cumul_enr_24h)

        #Calcul de la consommation moyenne d'énergie des foyers
        #On récupère les données du Zabbix
        try:
            zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
            zapi.login("liana", "b6!8Lw7DMbC7khUC")
            print(f"Connection to Zabbix server successful")
        except Exception as ex:
            print("Connection to Zabbix server could not be made due to the following error: \n", ex)
    
        print ("DEBUT TEST")
        for h in zapi.host.get(output="extend"):
            print(h['hostid'])
        print ("FIN TEST")
        puissance_foy_24h = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45201], output = "extend", limit = 1440):
            print(i['value'])
            puissance_foy_24h += i['value']
        print("Puissance foyers 24h : ", puissance_foy_24h)
        
        #history = zapi.history.get(hostids = [10084], itemids = [45201]) #on peut ajouter des paramètres pour un time from et time till vrai id : 44136
        #print ("History : ", history)
        #On met les données récupérées dans un dataframe pour pouvoir les manipuler
        #conso_foy = pd.DataFrame(history)
        #print("Conso foyers : ", conso_foy)
        #Requête SQL simple pour juste sommer toutes les consommations
        #query_somme = "SELECT SUM(value) FROM conso_foy"
        #test_somme = sqldf(query_somme)
        #print("TEST ULTIME : ", test_somme)
        #Il faudrait la diviser par le nombre de compteurs linky dispos (il y a surement une liste quelque part dans la bdd)
        with conn_coordo.engine.connect() as conn:
            nb_compteurs:int = pd.read_sql ("SELECT COUNT(*) FROM equipement_mesure_compteur_electrique", con = conn)
        print("Compteurs : ", nb_compteurs)
        
        puissance_en_Wh = puissance_foy_24h*24 #W en Wh
        cumul_en_Wh = cumul_enr_24h/1000 #kWh en Wh
        pourcentage_enr_conso_placee = 100*(cumul_en_Wh/puissance_en_Wh)
        print("Pourcentage de l'enr conso placée : ", pourcentage_enr_conso_placee)
    
        #Puis par une échelle de temps cohérente --> 24h glissantes
        return
        
    def pourcentage_autoconso() -> int:
        # Pour l'instant on ne va calculer que la quantité d'énergie produite (qui ne sera à terme que le dénominateur)
        # On va sommer les 6 indicateurs touchant à la production (3 éoliennes et 3 solaires) sur les dernières 24h (en Watts)
        # Si à terme il y a un nouvel indicateur qui s'ajoute pour un nouveau moyen de production (pour de la méthanisation par exemple)
        # il faudra rajouter une boucle for en remplaçant simplement l'itemids qui correspond à l'id dans le zabbix.
        # S'il s'agit d'un numérique non signé et non d'un nunmérique flottant comme tous les autres, il faudra également enlever le history = 0.
        
        #Connection au Zabbix
        try:
            zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
            zapi.login("liana", "b6!8Lw7DMbC7khUC")
            print(f"Connection to Zabbix server successful")
        except Exception as ex:
            print("Connection to Zabbix server could not be made due to the following error: \n", ex)
        
        #On initialise la production à 0 pour l'incrémenter en bouclant sur chaque indic de production du Zabbix
        prod_enr = 0
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 60 * 24)
        for i in zapi.history.get(hostids = [10084], itemids = [42882], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #ETLS_Puissance_solaire_ES1
        for i in zapi.history.get(hostids = [10084], itemids = [43112], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #ETLS_Puissance_solaire_ES2
        for i in zapi.history.get(hostids = [10084], itemids = [45200], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #ETLS_Puissance_solaire_ES3
        for i in zapi.history.get(hostids = [10084], itemids = [42868], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #ISW_Puissance_eolienne
        for i in zapi.history.get(hostids = [10084], itemids = [42833], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #BGW_Puissance_eolienne
        for i in zapi.history.get(hostids = [10084], itemids = [42869], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            prod_enr += int(i['value']) #TLV_Puissance_eolienne
        return prod_enr
    
    print("\n DEBUT pourcentage_autoconso")
    pourcentage_autoconso()
    print("FIN pourcentage_autoconso \n")
    
    #Encapsulation dans un csv
    filename = f"indics-{nowstr}.csv"
    finalpath = os.path.join(path, filename)
    print("Path : ", finalpath)
    #fichier = open(finalpath, "w")
    #/home/lblandin/Documents/Indicateurs-ELFE/indicateurs/indics.csv
    fichier = open(f"/home/lblandin/Documents/Indicateurs-ELFE/indicateurs/indics.csv", "w")
    
    appconn = indic_appareils_connectes()
    df1 = pd.DataFrame(appconn)
    print(df1)    
    res1 = df1.to_string (header=False, index = False)
    print(res1)
    fichier.write("\"Zabbix server\" Nombre_appareils_connectes_test " + res1 + "\n")
    
    pourcentage_app = pourcentage_app_lancés_24h()
    df2 = pd.DataFrame(pourcentage_app)
    print(df2)
    res2 = df2.to_string(header=False, index=False)
    print(res2)
    fichier.write("\"Zabbix server\" Pourcentage_app_lances_24h_test " + res2 + "\n")
    
    cumul_ener = [cumul_enr()]
    df_cumul = pd.DataFrame(cumul_ener)
    print(df_cumul)
    res_cumul = df_cumul.to_string(header=False, index=False)
    print(res_cumul)
    fichier.write("\"Zabbix server\" Cumul_energie_placee_test " + res_cumul + "\n")
        
    #Connection au Zabbix
    try:
        zab = ConnectionZabbix('192.168.30.111', 'Zabbix server')
        print(f"Connection to Zabbix made successfully.")
    except Exception as ex:
        print("Connection to Zabbix could not be made due to the following error: \n", ex)
    
    try:
        m1 = zb.Measurement(zab.host, "Nombre_appareils_connectes_test", res1)
        zab.measurements.add_measurement(m1)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
        
    
    try:
        m2 = zb.Measurement(zab.host, "Pourcentage_app_lances_24h_test", res2)
        zab.measurements.add_measurement(m2)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
    
    try:
        m_cumul = zb.Measurement(zab.host, "Cumul_energie_placee_test", res_cumul)
        zab.measurements.add_measurement(m_cumul)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
    
    try:
        await zab.response()
        print(f"Measurements well send to the Zabbix server")
    except Exception as ex:
        print("Measurements could not be send to the Zabbix server due to the following error: \n", ex)


if __name__ == "__main__":
    asyncio.run(main())