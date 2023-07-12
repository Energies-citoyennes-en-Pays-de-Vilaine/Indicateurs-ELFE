#from ZabbixSender import ZabbixSender, ZabbixPacket
import datetime
import asyncio_zabbix_sender as zb
import logging
import asyncio
from pyzabbix import ZabbixAPI

#logger = logging.getLogger("asyncio-zabbix-sender")
#logger.setLevel(logging.DEBUG)

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