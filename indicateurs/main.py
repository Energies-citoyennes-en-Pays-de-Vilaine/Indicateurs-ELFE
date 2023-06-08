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
        print(result)
    except Exception as ex:
        print("Table for result could not be made due to the following error: \n", ex)
        
    try:
        equipement_pilote_ou_mesure = conn2.get_table_with_schema('equipement_pilote_ou_mesure', 'bdd_coordination_schema')
        print(f"Table for equipement_pilote_ou_mesure created successfully.")
        print(equipement_pilote_ou_mesure)
    except Exception as ex:
        print("Table for equipement_pilote_ou_mesure could not be made due to the following error: \n", ex)
    
        
    #Calcul du nombre d'appareils connectés par 1/4h
    with conn1.engine.connect() as conn:
        appconn = pd.read_sql('SELECT COUNT(*) FROM result GROUP BY first_valid_timestamp ORDER BY first_valid_timestamp DESC LIMIT 1', con = conn)
        print(appconn)
        
    #Calcul du nombre d'appareils pilotés la semaine dernière
    with conn1.engine.connect() as conn:
        appsem = pd.read_sql('SELECT COUNT(DISTINCT machine_id) AS Nombre_appareils_pilotés_la_semaine_dernière FROM result WHERE first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 604800)', con = conn)
        print(appsem)
    
    #Calcul du pourcentage des appareils de ELFE lancés dans les dernières 24h
    with conn2.engine.connect() as conn:
        nb_app_EMS = pd.read_sql('SELECT COUNT(*) FROM equipement_pilote_ou_mesure', con=conn)
        #nb_app_EMS = pd.read_sql('SELECT COUNT(*) FROM equipement_pilote_ou_mesure WHERE equipement_pilote_ou_mesure_type_id = 131 OR equipement_pilote_ou_mesure_type_id = 515 OR equipement_pilote_ou_mesure_type_id = 155 OR equipement_pilote_ou_mesure_type_id = 151 OR equipement_pilote_ou_mesure_type_id = 112 OR equipement_pilote_ou_mesure_type_id = 111 OR equipement_pilote_ou_mesure_type_id = 113 OR equipement_pilote_ou_mesure_type_id = 221 OR equipement_pilote_ou_mesure_type_id = 225', con = conn)
        print(nb_app_EMS)
    with conn1.engine.connect() as conn:
        nb_app_lancés_24h = pd.read_sql('SELECT COUNT(*) FROM result WHERE first_valid_timestamp > (CAST(EXTRACT (epoch FROM NOW()) AS INT) - 86400)', con = conn)
        print(nb_app_lancés_24h)
    # machine_type = -1 => pas continue et 131 continu car correspond aux ballons d'eau chaude
    #Liste continu à terme (en prod) : 131, 151, 155
    #Liste pas continu à terme (en prod) : 515, 112, 111, 113, 221, 225
    
    #Test sqlalchemy
    #nb_app_lancés_24h = result.select().where(db.or_(db.and_(result.c.machine_type = 131, result.c.decisions_0 = )))
    #print(nb_app_lancés_24h) #Imprime le SQL
    #res1 = conn1.engine.connect().execute(nb_app_lancés_24h).fetchall() #extracting top 5 results
    #print(res1)
    
        
    #Connection au Zabbix
    try:
        zab = ConnectionZabbix('192.168.30.111', 'Zabbix server')
        print(f"Connection to Zabbix made successfully.")
    except Exception as ex:
        print("Connection to Zabbix could not be made due to the following error: \n", ex)
    
    try:
        m = zb.Measurement(zab.host, "Nombre_appareils_connectes", 5)
        zab.measurements.add_measurement(m)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
    
    try:
        await zab.response()
        print(f"Measurement well send to the Zabbix server")
    except Exception as ex:
        print("Measurement could not be send to the Zabbix server due to the following error: \n", ex)
    
    
    #Encapsulation dans un csv
    df = pd.DataFrame(appconn)
    print(df)
    fichier = open("indics.csv", "w")
    res = df.to_string (header=False, index = False)
    print(res)
    fichier.write("\"Zabbix server\" Nombre_appareils_connectes " + res) 


if __name__ == "__main__":
    asyncio.run(main())


"""
#Importation des packages nécessaires
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sqlalchemy as db
import sys
from sqlalchemy import select
from sqlalchemy import func

#main
#print(result.columns.keys()) #test
#print (db.select([result]).group_by(result.c.first_valid_timestamp))
print (db.select([func.count(result)]).group_by(result.c.first_valid_timestamp))
#db.select([db.func.sum(census.columns.pop2008).label('pop2008'), census.columns.sex]).group_by(census.columns.sex)
#db.select([census]).order_by(db.desc(census.columns.state), census.columns.pop2000)
#nb_appareils_pilotes = db.select([db.func.count()]).select_from(result)
#print("Nombre d'appareils pilotés : ", nb_appareils_pilotes)
"""