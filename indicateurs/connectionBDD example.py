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
    
    def __init__(self, nombdd:str, nomSchema : str = "public"):
        self.nomBDD = nombdd
        self.nomSchema = nomSchema
        #TODO Construction de l'URL : dialect+driver://username:password@host:port/database
        deburl = f"postgresql+psycopg2://username:password@ip_host:port/{self.nomBDD}"
        #Création de la connection à une BDD
        self.engine = db.create_engine (deburl, connect_args={"options": f"-csearch_path={self.nomSchema}"})
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
    
    def get_table_with_schema (self, table:str, schema:str) -> db.Table:
        return db.Table(table, self.metadata, schema=schema, autoload_with=self.engine)


