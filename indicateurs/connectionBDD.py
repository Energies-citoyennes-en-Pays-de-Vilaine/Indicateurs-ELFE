#Importation des packages nécessaires
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import sqlalchemy as db
import pandas as pd
import sys
from sqlalchemy import select

class ConnectionBDD:
    
    nomBDD:str
    engine:db.Engine
    metadata:db.MetaData
    
    def __init__(self, nombdd:str):
        self.nomBDD = nombdd
        #Construction de l'URL : dialect+driver://username:password@host:port/database
        deburl = 'postgresql+psycopg2://indicateurs:Cxj#j6A6KeR23R89@192.168.30.118:5432/'
        #Création de la connection à une BDD
        self.engine = db.create_engine (deburl+self.nomBDD)
        #Création du métadata pour accéder à des tables de la BDD
        self.metadata = db.MetaData()
        self.metadata.reflect = True

    # Getters
    def get_nomBDD(self):
        return self.nomBDD
    
    def get_engine(self) -> db.Engine :
        return self.engine

    def get_metadata(self) -> db.MetaData:
        return self.metadata

    #Importation d'une table grâce au métadata
    def get_table(self, table:str) -> db.Table :
        return db.Table(table, self.metadata, autoload_with=self.engine)


