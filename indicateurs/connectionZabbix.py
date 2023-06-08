#from ZabbixSender import ZabbixSender, ZabbixPacket
import datetime
import asyncio_zabbix_sender as zb
import logging
import asyncio

logger = logging.getLogger("asyncio-zabbix-sender")
logger.setLevel(logging.DEBUG)

"""
sender = zb.ZabbixSender("192.168.30.111")

measurements = zb.Measurements([
    zb.Measurement(
        sender, "Zabbix server", 5, datetime.datetime.utcnow()
    )
])

response = await sender.send(measurements)
"""


#packet = [ZabbixMetric('Zabbix server', 'ombre_appareils_connectes', 2)]
#result = ZabbixSender(use_config=True).send(packet)

#server = ZabbixSender('192.168.30.111', 10051)
#packet = ZabbixPacket()
#packet.add('Zabbix server','Nombre_appareils_connectes', '5') # + timestamp unixtime ?
#server.send(packet) #marche pas
#print(server.status)


class ConnectionZabbix:

    sender:zb.ZabbixSender #ip du serveur, pour celui d'EPV : 192.168.30.111
    host:str #hôte zabbix, pour les indicateurs : Zabbix server
    measurements:zb.Measurements #liste de measurement initialisée à vide et à laquelle on peut ajouter des éléments
    #sender = ZabbixSender('192.168.30.111')
    
    def __init__(self, ipserver:str, host:str):
        self.sender = zb.ZabbixSender(ipserver)
        self.host = host
        self.measurements = zb.Measurements([])
    
    def add(self, key:str, val:int):
        self.measurements.add_measurement(zb.Measurement(self.sender, self.host, val))

    async def response(self):
        return await self.sender.send(self.measurements)


"""
#!/bin/bash

## 1° le dernier point, au bout de la courbe
PGPASSWORD=7UJd9U9W1pgkRK11 psql -c "SELECT * from p_c_with_flexible_consumption ORDER BY data_timestamp DESC LIMIT 1" -h 192.168.30.119 -d ems_sortie -U zbx_monitor --csv | grep -v data > prevision_dernier.csv

sed -i 's/,/ /g' prevision_dernier.csv
sed -i 's/^/- Prevision_ems_ancien /' prevision_dernier.csv

zabbix_sender -c /etc/zabbix/zabbix_agent2.conf -T -i prevision_dernier.csv

## 2° la dernière journée, en remplaçant la courbe
PGPASSWORD=7UJd9U9W1pgkRK11 psql -c "SELECT * from p_c_with_flexible_consumption ORDER BY data_timestamp DESC LIMIT 96" -h 192.168.30.119 -d ems_sortie -U zbx_monitor --csv | grep -v data > prevision.csv
sed -i 's/,/ /g' prevision.csv

cp prevision.csv prevision_new.csv
sed -i 's/^/- Prevision_ems /' prevision_new.csv

#Clear history
url="http://mqtt.projet-elfe.fr/api_jsonrpc.php"

auth=$(curl -s -X POST -H 'Content-Type: application/json-rpc' \
-d '
{"jsonrpc":"2.0","method":"user.login","params":
{"user":"TODO","password":"TODO"},
"id":1,"auth":null}
' $url | \
jq -r .result
)

erase=$(curl -s -X POST -H 'Content-Type: application/json-rpc' \
-d '{"jsonrpc":"2.0","method":"history.clear","params": ["44119"],"id":1,"auth":"'$auth'"}' $url)

zabbix_sender -c /etc/zabbix/zabbix_agent2.conf -T -i prevision_new.csv

## 3° La dernière journée, ajoutée à la courbe existante en gardant l'historique
cp prevision.csv prevision_cumul.csv
sed -i 's/^/- Prevision_ems_cumul /' prevision_cumul.csv

zabbix_sender -c /etc/zabbix/zabbix_agent2.conf -T -i prevision_cumul.csv
"""