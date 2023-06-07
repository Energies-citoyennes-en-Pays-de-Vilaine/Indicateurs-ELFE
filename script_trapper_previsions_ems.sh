#!/bin/bash

## 1° le dernier point, au bout de la courbe
#PGPASSWORD=7UJd9U9W1pgkRK11 psql -c "SELECT * from p_c_with_flexible_consumption ORDER BY data_timestamp DESC LIMIT 1" -h 192.168.30.119 -d ems_sortie -U zbx_monitor --csv | grep -v data > prevision_dernier.csv

#sed -i 's/,/ /g' prevision_dernier.csv
#sed -i 's/^/- Prevision_ems_ancien /' prevision_dernier.csv

zabbix_sender -z 192.168.30.111 -p 10051 -s "Zabbix server" -i indics.csv

# format du fichier csv (séparer par des espaces) : hostname key (timestamp) value (timestamp optionnel si on enlève le -T avant le -i il prendra le moment de maintenant)
# zabbix_sender -z 192.168.30.111 -p 10051 -s "Zabbix server" -k Nombre_appareils_connectes -o "4"