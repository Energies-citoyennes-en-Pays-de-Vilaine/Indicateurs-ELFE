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