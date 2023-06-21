"""
sql = '''
    SELECT * FROM result
'''
#with engine.connect() as conn:
#    query = conn.execute(text(sql))         
#df = pd.DataFrame(query.fetchall())

with engine.connect() as conn:
    df = pd.read_sql('SELECT * FROM p_c_with_flexible_consumption WHERE data_timestamp>1685000700', con = conn)

# SELECT COUNT(*) FROM Actor
result = db.select([db.func.count()]).select_from(actor_table).scalar()
print("Count:", result)

#Calcul du nombre d'appareils pilotés
def nb_appareils_pilotes():
    return db.select([result]).group_by(result.c.first_valid_timestamp).order_by(db.desc(result.c.first_valid_timestamp))
"""

import asyncio
from connectionBDD import *
from connectionZabbix import *
from datetime import datetime
import sys
import pandas as pd
import os
import subprocess
import shutil
import csv


#Calcul du nombre d'appareils connectés par 1/4h
def indic_appareils_connectes() -> int : 
    conn_sortie = ConnectionBDD('preprod_sortie_ems') 
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
