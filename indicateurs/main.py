from connectionBDD import *
import sys

def main():
    
    bdd1 = 'preprod_sortie_ems'
    bdd2 = 'preprod_bdd_coordination'
    bdd3 = 'preprod_historisation'
    
    try:
        conn1 = ConnectionBDD(bdd1)
        print(f"Connection to " +bdd1+ " created successfully.")
    except Exception as ex:
        print("Connection to " +bdd1+ " could not be made due to the following error: \n", ex)
        
    try:
        conn2 = ConnectionBDD(bdd2)
        print(f"Connection to " +bdd2+ " created successfully.")
    except Exception as ex:
        print("Connection to " +bdd2+ " could not be made due to the following error: \n", ex)
        
    try:
        conn3 = ConnectionBDD(bdd3)
        print(f"Connection to " +bdd3+ " created successfully.")
    except Exception as ex:
        print("Connection to " +bdd3+ " could not be made due to the following error: \n", ex)
    
    try:
        result = conn1.get_table('result')
        print(f"Table for result created successfully.")
    except Exception as ex:
        print("Table for result could not be made due to the following error: \n", ex)
    

if __name__ == "__main__":
    sys.exit(main())


"""
#Importation des packages nécessaires
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sqlalchemy as db
import pandas as pd
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