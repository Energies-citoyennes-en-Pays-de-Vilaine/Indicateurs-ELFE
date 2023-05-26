"""import pyodbc

connection = pyodbc.connect('Driver={SQL Server Native Client 11.0};'
                            'Server=192.168.30.118;'
                            'Database=preprod_sortie_ems;'
                            'Trusted_Connection=yes')
cursor = connection.cursor()
cursor.execute('SELECT * FROM result WHERE data_timestamp>1685000700')
pyodbc.SQL_DRIVER_ODBC_VER

for i in cursor:
    print(i)
    """
    
#import psycopg2
""""
connection = psycopg2.connect(dbname="preprod_sortie_ems", host="192.168.30.118", user="indicateurs", password="Cxj#j6A6KeR23R89")
cursor = connection.cursor()
#cursor.execute('SELECT * FROM result WHERE data_timestamp>1685000700')"""

#import sqlalchemy
#engine = create_engine("postgresql://indicateurs:Cxj#j6A6KeR23R89@192.168.30.118:")
# IMPORT THE SQALCHEMY LIBRARY's CREATE_ENGINE METHOD
"""
# DEFINE THE DATABASE CREDENTIALS
user = 'indicateurs'
password = 'Cxj#j6A6KeR23R89'
host = '192.168.30.118'
port = 5432
database = 'preprod_sortie_ems'

# PYTHON FUNCTION TO CONNECT TO THE MYSQL DATABASE AND RETURN THE SQLACHEMY ENGINE OBJECT
def get_connection():
    return create_engine(
        url="postgresql+psycopg2://{0}:{1}@{2}:{3}/{4}".format(
            user, password, host, port, database
        )
    )

if __name__ == '__main__':
    try:
        # GET THE CONNECTION OBJECT (ENGINE) FOR THE DATABASE
        engine = get_connection()
        print(
            f"Connection to the {host} for user {user} created successfully.")
    except Exception as ex:
        print("Connection could not be made due to the following error: \n", ex)
"""

#Importation des packages nécessaires
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sqlalchemy
import pandas as pd

#Définition de l'url de connection et des noms des bdds
deburl = 'postgresql+psycopg2://indicateurs:Cxj#j6A6KeR23R89@192.168.30.118:5432/'
bdd1 = 'preprod_sortie_ems'
bdd2 = 'preprod_bdd_coordination'
bdd3 = 'preprod_historisation'
bdd4 = 'root'
#Construction de l'URL : dialect+driver://username:password@host:port/database

#Création de la connection à une BDD
def get_connection(nombdd):
    return sqlalchemy.create_engine (deburl+nombdd)

#Test de la connection avec affichage du succès ou non
def test_connection(nombdd):
    try:
        engine = get_connection(nombdd)
        print(
            f"Connection to " +nombdd+ " created successfully.")
    except Exception as ex:
        print("Connection to " +nombdd+ " could not be made due to the following error: \n", ex)

#Connection et test à toutes les bdds
if __name__ == '__main__':
    test_connection(bdd1)
    test_connection(bdd2)
    test_connection(bdd3)
    test_connection(bdd4)

"""
sql = '''
    SELECT * FROM result
'''
#with engine.connect() as conn:
#    query = conn.execute(text(sql))         
#df = pd.DataFrame(query.fetchall())

with engine.connect() as conn:
    df = pd.read_sql('SELECT * FROM p_c_with_flexible_consumption WHERE data_timestamp>1685000700', con = conn)
    """

