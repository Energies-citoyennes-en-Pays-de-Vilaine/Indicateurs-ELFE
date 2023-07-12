from pyzabbix import ZabbixAPI

def createZapi() -> ZabbixAPI:
    zapi = ZabbixAPI("lien vers le serveur")
    zapi.login("nom d'utilisateur", "mot de passe")
    return zapi