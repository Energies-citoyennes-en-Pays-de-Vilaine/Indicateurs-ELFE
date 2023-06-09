import asyncio
from connectionBDD import *
from connectionZabbix import *
import sys
import pandas as pd
import os
import subprocess
import shutil
import csv


async def main():
    
    bdd1 = 'preprod_sortie_ems'
    bdd2 = 'preprod_bdd_coordination'
    bdd3 = 'preprod_historisation'
    
    #Connection aux 3 BDD
    try:
        conn1 = ConnectionBDD(bdd1)
        print(f"Connection to " +bdd1+ " created successfully.")
    except Exception as ex:
        print("Connection to " +bdd1+ " could not be made due to the following error: \n", ex)
        
    try:
        conn2 = ConnectionBDD(bdd2, "bdd_coordination_schema")
        print(f"Connection to " +bdd2+ " created successfully.")
    except Exception as ex:
        print("Connection to " +bdd2+ " could not be made due to the following error: \n", ex)
        
    try:
        conn3 = ConnectionBDD(bdd3)
        print(f"Connection to " +bdd3+ " created successfully.")
    except Exception as ex:
        print("Connection to " +bdd3+ " could not be made due to the following error: \n", ex)
    
    #Connection aux tables dont on a besoin
    try:
        result = conn1.get_table('result')
        print(f"Table for result created successfully.")
    except Exception as ex:
        print("Table for result could not be made due to the following error: \n", ex)
        
    try:
        withflex = conn1.get_table('p_c_with_flexible_consumption')
        print(f"Table for p_c_with_flexible_consumption created successfully.")
    except Exception as ex:
        print("Table for p_c_with_flexible_consumption could not be made due to the following error: \n", ex)
        
    try:
        withoutflex = conn1.get_table('p_c_without_flexible_consumption')
        print(f"Table for p_c_without_flexible_consumption created successfully.")
    except Exception as ex:
        print("Table for p_c_without_flexible_consumption could not be made due to the following error: \n", ex)
        
    try:
        equipement_pilote_ou_mesure = conn2.get_table_with_schema('equipement_pilote_ou_mesure', 'bdd_coordination_schema')
        print(f"Table for equipement_pilote_ou_mesure created successfully.")
    except Exception as ex:
        print("Table for equipement_pilote_ou_mesure could not be made due to the following error: \n", ex)
    
        
    #Calcul du nombre d'appareils connectés par 1/4h
    with conn1.engine.connect() as conn:
        appconn = pd.read_sql("SELECT COUNT(*) FROM result\
                                GROUP BY first_valid_timestamp\
                                ORDER BY first_valid_timestamp DESC\
                                LIMIT 1"\
                                , con = conn)
        print(appconn)
        
    #Calcul du nombre d'appareils pilotés la semaine dernière
    with conn1.engine.connect() as conn:
        appsem = pd.read_sql("SELECT COUNT(DISTINCT machine_id) AS Nombre_appareils_pilotés_la_semaine_dernière FROM result\
                                WHERE first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 604800)", con = conn)
        print(appsem)
    
    #Calcul du pourcentage des appareils de ELFE lancés dans les dernières 24h
    #Il faudra rajouter des clauses OR si de nouveaux types apparaissent, sans ajouter les compteurs
    with conn2.engine.connect() as conn:
        nb_app_EMS = pd.read_sql("SELECT COUNT(*) FROM equipement_pilote_ou_mesure\
                                    WHERE equipement_pilote_ou_mesure_type_id = 131\
                                        OR equipement_pilote_ou_mesure_type_id = 515\
                                        OR equipement_pilote_ou_mesure_type_id = 155\
                                        OR equipement_pilote_ou_mesure_type_id = 151\
                                        OR equipement_pilote_ou_mesure_type_id = 112\
                                        OR equipement_pilote_ou_mesure_type_id = 111\
                                        OR equipement_pilote_ou_mesure_type_id = 113\
                                        OR equipement_pilote_ou_mesure_type_id = 221\
                                        OR equipement_pilote_ou_mesure_type_id = 225"\
                                , con = conn)
        print("nb app EMS : " , nb_app_EMS)
        
    with conn1.engine.connect() as conn:
        
        nb_app_lancés_24h_continu = pd.read_sql('SELECT COUNT(DISTINCT machine_id) FROM result WHERE machine_type = 131 AND decisions_0 = 1 AND first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)', con = conn)
        print("nb app lancés 24h continu : " , nb_app_lancés_24h_continu)
        #nb_app_lancés_24h_discontinu = pd.read_sql('SELECT COUNT(*) FROM result WHERE machine_type = -1 AND decisions_0 = 1 AND first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)', con = conn)
        #print("nb app lancés 24h discontinu : " , nb_app_lancés_24h_discontinu)
        nb_app_lancés_24h_discontinu = pd.read_sql("SELECT COUNT(*) FROM result AS r1 \
                                                    INNER JOIN  result AS r2 ON r1.machine_id = r2.machine_id\
                                                    WHERE r2.machine_type = -1\
                                                        AND r2.first_valid_timestamp = r1.first_valid_timestamp + 900\
                                                        AND r2.decisions_0 = 0\
                                                        AND r1.decisions_0 = 1\
                                                        AND r2.first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)"
                                        , con = conn)
        print("nb app lancés 24h discontinu : " , nb_app_lancés_24h_discontinu)
        
        nb_app_lancés_24h = nb_app_lancés_24h_continu + nb_app_lancés_24h_discontinu
        print("nb app lancés 24h : ", nb_app_lancés_24h)
        
    pourcentage_app_lancés_24h = (100*nb_app_lancés_24h)/nb_app_EMS
    print ("pourcentage app lancés 24h : ", pourcentage_app_lancés_24h)        
    # machine_type = -1 => pas continue et 131 continu car correspond aux ballons d'eau chaude
    #Liste continu à terme (en prod) : 131, 151, 155
    #Liste pas continu à terme (en prod) : 515, 112, 111, 113, 221, 225
    
    #Calcul du cumul de kW d'énergie placés par l'EMS depuis le début du projet
    with conn1.engine.connect() as conn:
        #cumul_enr = pd.read_sql("SELECT * FROM p_c_with_flexible_consumption LIMIT 10", con=conn)
        cumul_enr = pd.read_sql("SELECT SUM(withflex.power - withoutflex.power)\
                                    FROM p_c_with_flexible_consumption AS withflex\
                                    INNER JOIN p_c_without_flexible_consumption AS withoutflex\
                                    ON withflex.data_timestamp = withoutflex.data_timestamp\
                                    \
                                    LIMIT 96"
                                    , con = conn)
        print(cumul_enr)
        
    #ça marche comme ça mais il faut trouver un moyen de remettre le order by
    # ORDER BY withflex.data_timestamp DESC\
                               #     LIMIT 96

    
    #Encapsulation dans un csv
    df1 = pd.DataFrame(appconn)
    print(df1)
    df2 = pd.DataFrame(pourcentage_app_lancés_24h)
    print(df2)
    fichier = open("indics.csv", "w")
    res1 = df1.to_string (header=False, index = False)
    print(res1)
    fichier.write("\"Zabbix server\" Nombre_appareils_connectes " + res1 + "\n")
    res2 = df2.to_string(header=False, index=False)
    print(res2)
    fichier.write("\"Zabbix server\" Pourcentage_app_lances_24h " + res2)
        
    #Connection au Zabbix
    try:
        zab = ConnectionZabbix('192.168.30.111', 'Zabbix server')
        print(f"Connection to Zabbix made successfully.")
    except Exception as ex:
        print("Connection to Zabbix could not be made due to the following error: \n", ex)
    
    try:
        m1 = zb.Measurement(zab.host, "Nombre_appareils_connectes", res1)
        zab.measurements.add_measurement(m1)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
        
    """
    try:
        m2 = zb.Measurement(zab.host, "Pourcentage_app_lances_24h", res2)
        zab.measurements.add_measurement(m2)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
    """
    
    try:
        await zab.response()
        print(f"Measurements well send to the Zabbix server")
    except Exception as ex:
        print("Measurements could not be send to the Zabbix server due to the following error: \n", ex)


if __name__ == "__main__":
    asyncio.run(main())