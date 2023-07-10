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

"""
#Enabling debug logging for the pyzabbix API
stream = logging.StreamHandler(sys.stdout)
stream.setLevel(logging.DEBUG)
log = logging.getLogger('pyzabbix')
log.addHandler(stream)
log.setLevel(logging.DEBUG)
"""

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
            return int(cumul_enr*1000)
    
    #Calcul du cumul de kW d'énergie placés par l'EMS depuis le début du projet
    def cumul_enr_opti() -> int:
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
                                                                (SELECT first_valid_timestamp/86400 AS day, machine_id, machine_type FROM result
                                                                        WHERE decisions_0 = 1) AS T1) AS T2
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
            return int(cumul_enr*1000)
    
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
        print ("Enr placée 24h : ", cumul_enr_placee_24h)
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
    
    def cumul_enr_autoconso_opti() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 60 * 24)
        #Récupération de la précédente valeur
        val_prec = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45255], time_from = tf, time_till = tt-5, output = "extend", limit = 1, history=0):
            val_prec = int(float(i['value']))
        #Calcul de la production mise à l'échelle sur l'heure (en Wh)
        enr_prod_mae = 0
        for i in zapi.history.get(hostids = [10084], itemids = [44969], time_from = tf, time_till = tt, output = "extend", limit = 5, history=0):
            enr_prod_mae += int(float(i['value']))*(1/20) #Panel_Prod_puissance_mae : 1 valeur toutes les 3 min
        #Calcul de la production en surplus à partir de l'équilibre (en Wh)
        surplus_prod = 0
        for i in zapi.history.get(hostids = [10084], itemids = [42883], time_from = tf, time_till = tt, output = "extend", limit = 15, history=0):
            if (float(i['value'])>0):
                surplus_prod += int(float(i['value']))*(1/60) #equilibre_general_p_c : 1 valeur par minute
        #Calcul de l'enr produite et consommée sur le territoire
        cumul_supp = int(enr_prod_mae - surplus_prod)
        cumul_autoconso = val_prec + cumul_supp
        return cumul_autoconso
    
    def pourcentage_autoconso_30j() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 60 * 24 * 30.5)
        #Calcul de l'enr produite et consommée sur le territoire le mois dernier
        enr_prod_mae = 0 #Production mise à l'échelle sur l'heure (en Wh)
        for i in zapi.history.get(hostids = [10084], itemids = [44969], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            enr_prod_mae += int(float(i['value']))*(1/20)
        surplus_prod = 0 #Production en surplus à partir de l'équilibre (en Wh)
        for i in zapi.history.get(hostids = [10084], itemids = [42883], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            if (float(i['value'])>0):
                surplus_prod += int(float(i['value']))*(1/60)
        enr_prod_et_conso = int(enr_prod_mae - surplus_prod) #Enr produite et consommée sur le territoire
        #Calcul de la production mise à l'échelle du panel le mois dernier
        enr_prod = 0
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 60 * 24)
        for i in zapi.history.get(hostids = [10084], itemids = [44969], time_from = tf, time_till = tt, output = "extend", limit = 1440, history=0):
            enr_prod += int(float(i['value'])) #Panel_Prod_puissance_mae
        #Calcul du pourcentage d'autoconsommation
        pourcentage_autoconso = int(100 * (enr_prod_et_conso/enr_prod))
        return pourcentage_autoconso
    
    def enr_eolien() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 15)
        #Calcul de l'énergie éolienne des 15 dernières minutes à partir de la puissance
        enr_eol = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45197], time_from = tf, time_till = tt, output = "extend", limit = 15, history=0):
            enr_eol += int(float(i['value']))*(1/60) #Prod_eolienne
        return int(enr_eol)
    
    def enr_solaire() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 15)
        #Calcul de l'énergie solaire des 15 dernières minutes à partir de la puissance
        enr_sol = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45198], time_from = tf, time_till = tt, output = "extend", limit = 15, history=0):
            enr_sol += int(float(i['value']))*(1/60) #Prod_solaire
        return int(enr_sol)
    
    def enr_metha() -> int:
        #Connection au Zabbix
        zapi = ZabbixAPI("http://mqtt.projet-elfe.fr")
        zapi.login("liana", "b6!8Lw7DMbC7khUC")
        tt = int(time.mktime(datetime.now().timetuple()))
        tf = int(tt - 60 * 15)
        #Calcul de l'énergie métha des 15 dernières minutes à partir de la puissance
        enr_meth = 0
        for i in zapi.history.get(hostids = [10084], itemids = [45248], time_from = tf, time_till = tt, output = "extend", limit = 15, history=0):
            enr_meth += int(float(i['value']))*(1/60) #Prod_methanisation
        return int(enr_meth)
    
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
    
    print("\n DEBUT")
    print("Enr eolien : ", enr_eolien())
    print("Enr solaire : ", enr_solaire())
    print("Enr metha : ", enr_metha())
    print("FIN \n")
    
    #Encapsulation dans un csv
    filename = f"indics-{nowstr}.csv"
    finalpath = os.path.join(path, filename)
    print("Path : ", finalpath)
    fichier = open(f"/home/lblandin/Documents/Indicateurs-ELFE/indicateurs/indics.csv", "w")
    
    appconn = indic_appareils_connectes()
    df1 = pd.DataFrame(appconn)    
    res1 = df1.to_string (header=False, index = False)
    fichier.write("\"Zabbix server\" Nombre_appareils_connectes_test " + res1 + "\n")
    
    pourcentage_app = pourcentage_app_lancés_24h()
    df2 = pd.DataFrame(pourcentage_app)
    res2 = df2.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Pourcentage_app_lances_24h_test " + res2 + "\n")
    
    cumul_ener = [cumul_enr()]
    df_cumul = pd.DataFrame(cumul_ener)
    res_cumul = df_cumul.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Cumul_energie_placee_test " + res_cumul + "\n")
    
    conso_ener_placee = [conso_enr_placee()]
    df_conso = pd.DataFrame(conso_ener_placee)
    res_conso = df_conso.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Pourcentage_energie_consommee_placee_test " + res_conso + "\n")
    
    cumul_ener_autoconso = [cumul_enr_autoconso_opti()]
    df_cautoconso = pd.DataFrame(cumul_ener_autoconso)
    res_cautoconso = df_cautoconso.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Energie_autoconsommee_test " + res_cautoconso + "\n")
    
    pourcentage_autoconso = [pourcentage_autoconso_30j()]
    df_pautoconso = pd.DataFrame(pourcentage_autoconso)
    res_pautoconso = df_pautoconso.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Pourcentage_autoconsommation_test " + res_pautoconso + "\n")
    
    enr_eol = [enr_eolien()]
    df_enreol = pd.DataFrame(enr_eol)
    res_enreol = df_enreol.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Enr_eolienne_test " + res_enreol + "\n")
    
    enr_sol = [enr_solaire()]
    df_enrsol = pd.DataFrame(enr_sol)
    res_enrsol = df_enrsol.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Enr_solaire_test " + res_enrsol + "\n")
    
    enr_meth = [enr_metha()]
    df_enrmeth = pd.DataFrame(enr_meth)
    res_enrmeth = df_enrmeth.to_string(header=False, index=False)
    fichier.write("\"Zabbix server\" Enr_methanisation_test " + res_enrmeth + "\n")
    
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
        m_conso = zb.Measurement(zab.host, "Pourcentage_energie_consommee_placee_test", res_conso)
        zab.measurements.add_measurement(m_conso)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
    
    try:
        m_cautoconso = zb.Measurement(zab.host, "Energie_autoconsommee_test", res_cautoconso)
        zab.measurements.add_measurement(m_cautoconso)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
    
    try:
        m_pautoconso = zb.Measurement(zab.host, "Pourcentage_autoconsommation_test", res_pautoconso)
        zab.measurements.add_measurement(m_pautoconso)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
        
    try:
        m_enreol = zb.Measurement(zab.host, "Enr_eolienne_test", res_enreol)
        zab.measurements.add_measurement(m_enreol)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
        
    try:
        m_enrsol = zb.Measurement(zab.host, "Enr_solaire_test", res_enrsol)
        zab.measurements.add_measurement(m_enrsol)
        print(f"Creation of the measurement and adding made successfully.")
    except Exception as ex:
        print("Creation of the measurement or adding could not be made due to the following error: \n", ex)
        
    try:
        m_enrmeth = zb.Measurement(zab.host, "Enr_methanisation_test", res_enrmeth)
        zab.measurements.add_measurement(m_enrmeth)
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