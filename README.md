# Indicateurs-ELFE

## Contexte

Ce document s'attache à décrire le plus précisément possible le fonctionnement du code du projet *Indicateurs-ELFE* afin qu'il puisse être comris et repris. Le but premier de ce projet est de calculer une série d'indicateurs à destination des utilisateurs afin de mesurer l'impact du projet dans son ensemble. Ces indicateurs ont vocation à être repris sur le tableau de bord général de ELFE sur la plateforme Viriya.

## Arborescence

Dossier indicateurs
- \__pycache__ : cache du projet généré automatiquement
- *connectionBDD.py* : classe avec ses fonctions utiles à la connexion à la base de données (BDD) de la pré-production et à ses tables.
- *connectionBDDProd.py* : classe avec ses fonctions utiles à la connexion à la base de données de la production et à ses tables
- *connectionZabbix.py* : classe avec ses fonctions utiles à la connexion au serveur, à l'ajout et à l'envoi des données.
- *indicateurs.service* : fichier nécessaire à l'automatisation, c'est le service qui envoie les nouvelles valeurs des indicateurs.
- *indicateurs.timer* : fichier nécessaire à l'automatisation, il appelle le service toutes les 15 min.
- *indic.csv* : fichier généré à chaque mise à jour de la pré-production, il contient les nouvelles valeurs de chaque indicateur.
- *indic-prod.csv* : fichier généré à chaque mise à jour de la production, il contient les nouvelles valeurs de chaque indicateur.
- *main.py* : programme principal qui appelle toutes les fonctions et calcule tous les indicateurs nécessaires à la pré-production. Il est automatisé localement sur des indicateurs de test.
- *prod.py* : programme principal qui appelle toutes les fonctions et calcule tous les indicateurs nécessaires à la production. Il est automatisé sur le serveur sur les indicateurs finaux, qui sont eux-mêmes appelés par la plateforme Viriya.

NB : Les identifiants à fournir pour les connexions à la base de données sont à indiquer dans la variable deburl du constructeur de la classe ConnectionBDDProd.

***

## Connexion à la base de données et à ses tables

Librairie utilisée : **sqlalchemy**

### Connection à la base de données

- **l. 17-18** : On définit d'abord des variables correspondants à chaque base de données dont on va se servir.
- **l. 21-22** : Puis on crée une instance de la classe ConnectionBddProd par base de données. Si le nom du schéma n'est pas "public" il est nécessaire de le préciser en deuxième paramètre du constructeur (définit par défaut à "public"). Ces connexions sont nécessaires pour accéder aux données ensuite. Le constructeur de ConnectionBDDProd attribut un nom (le 1er paramètre), un engine crée à partir de plusieurs éléments (langage, driver, IP, identifiants à la BDD), et un métadata par défaut. 

### Connection aux tables

- **l. 27-31** : Création d'une connexion à chaque table via les connexions créées. C'est l'objet métadata de la connexion qui est utilisé.

***

## Calcul des indicateurs

Librairie utilisée : **sqlalchemy**

### Calcul du nombre d'appareils connectés par 1/4h

- Objectif de calcul : On cherche à calculer le nombre d'appareils que ELFE peut lancer actuellement. Ce sont donc les appareils que les utilisateur.rice.s ont demandé à lancer, via un ELFI ou Viriya, mais que ELFE n’a pas encore lancé. Il est recalculé tous les quarts d’heure.

- Source(s) de données : table result de la BDD ems_sortie

- Méthode de calcul (explication du SQL) : Dans la table result, il y a une ligne par quart d'heure et par machine activée à ce moment, celles que l'EMS réfléchit à lancer ou non. On compte donc simplement le nombre de lignes correspondant au dernier timestamp (colonne first_valid_timestamp). Pour être sûr de n'avoir que ce dernier timestamp, on ordonne les lignes par first_valid_timestamp descendant (ORDER BY first_valid_timestamp DESC), on groupe par first_valid_timestamp pour n'avoir qu'une ligne par timestamp avec le nombre de machines correspondant (GROUP BY first_valid_timestamp), et on limite les lignes résultat à un pour ne garder que le timestamp le plus récent (LIMIT 1).

- Indicateur Zabbix correspondant :
> * Nom : Nombre_d'appareils_connectés
> * Clé : Nombre_appareils_connectes
> * Id : 45189

### Calcul du pourcentage des appareils de ELFE lancés dans les dernières 24h

- Objectif de calcul : On cherche à calculer le pourcentage des appareils enregistrés dans ELFE et que l'EMS peut piloter qui ont été lancés dans les dernières 24 heures.

- Source(s) de données : table equipement_pilote_ou_mesure de la BDD bdd_coordination, table result de la BDD ems_sortie

- Méthode de calcul (explication du SQL) : 
> 1. On calcule d'abord le nombre d'appareils pilotables par l'EMS : on exclue donc les compteurs et les producteurs. Cela servira de base pour faire le pourcentage.
> 2. On calcule ensuite le nombre de lancement qui ont eu lieu depuis 24h. On garde ensemble les appareils continus et discontinus. Les conditions ici appliquées pour la sélection des appareils à compter sont :
    - decisions_0 = 1 : cela signifie que l'EMS a choisi de lancer l'appareil au prochain quart d'heure. Cependant, cela nous oblige à compter par machine_id distincts puisqu'il arrive souvent que l'appareil ne se lance en fait pas et que la même décision soit reprise au quart d'heure suivant. On part donc du postulat que rares sont les personnes à lancer leur lave-vaisselle trois fois en 24h, et on prent le parti de ne compter qu'une fois par jour les machines fonctionnant en continu.
    - timestamp > (maintenant - 24h) : cela permet de ne garder bien que les appareils lancés dans les dernières 24h.
> 3. On met enfin le résultat de la fraction des deux (1. / 2.) sous forme de pourcentage, en ne gardant qu'un seul chiffre après la virgule.

- Indicateur Zabbix correspondant : 
> * Nom : Pourcentage d'appareils lancés dans les dernières 24h
> * Clé : Pourcentage_app_lances_24h
> * Id : 45201

### Calcul du cumul d'énergie placés par l'EMS depuis le début du projet

- Objectif de calcul : On cherche à calculer la quantité d’énergie placée par ELFE depuis le début du projet, c'est-à-dire l'énergie consommée par chaque appareil lancé par l'EMS.

- Source(s) de données :  table result de la BDD ems_sortie, equipement_pilote_consommation_moyenne de la BDD bdd_coordination

- Méthode de calcul (explication du SQL) :
> 1. On fabrique deux tables sous la forme machine_type | nombre de lancements, une pour les machines continues, et une pour les machines discontinues. Pour les machines discontinues, on compte chaque lancement indiqué dans la table result. Pour les machines continues, on compte un lancement par jour puisque la valeur de decisions_0 reste à 1 tant que la machine reste allumée.\
Les machinie_type considérés actuellement comme continus ou discontinus sont les suivants : \
Liste continu à terme (en prod) : 131, 151, 155\
Liste discontinu à terme (en prod) : 515, 112, 111, 113, 221, 225\
Si des machines types sont ajouter, il faudra donc en ajouter à ces listes dans les conditions "machine_type IN (...) des variables coeffs_continu et coeffs_discontinu.
> 2. On récupère la table equipement_pilote_consommation_moyenne qui contient une valeur de consommation moyenne par cycle en Wh pour chaque type d'appareil. Ces moyennes sont calculées avec les données et les appareils dont nous disposons actuellement, mais il serait peut-être pertinent à l'avenir de les recalculer si beaucoup d'appareils se rajoutent.
> 3. Enfin, on multiplie le nombre de lancement de chaque machine_type avec la consommation moyenne correspondante et on agrège le tout. On divise le résultat par 1000 puisqu'on a des Wh et qu'on veut des kWh.

- Indicateur Zabbix correspondant : 
> * Nom : Cumul énergie placée
> * Clé : Cumul_energie_placee
> * Id : 45240

### Calcul du pourcentage de la consommation d'énergie des foyers placée

- Objectif de calcul : On cherche à calculer ce que représente l'énergie placée par ELFE dans la consommation d'énergie totale des foyers.

- Source(s) de données :  table p_c_with_flexible_consumption de la BDD ems_sortie, table p_c_without_flexible_consumption de la BDD ems_sortie, indicateur Zabbix de clé  Panel_R_puissance_mae et d'id 44968

- Méthode de calcul (explication du SQL) : 
> 1. On commence par calculer l'énergie placée par l'EMS dans les dernières 24 heures en soustrayant les colonnes power des tables p_c_with_flexible_consumption et p_c_without_flexible_consumption pour un même timestamp. On sélectionne les timestamp correspondants aux dernières 24 heures.
> 2. On calcule la consommation du panel mise à l'échelle en additionnant les valeurs sur les dernières 24 heures de l'indicateur Zabbix Panel_R_puissance_mae.
> 3. Enfin, on calcule le pourcentage correspondant à la fraction de 1./2..

- Indicateur Zabbix correspondant : 
> * Nom : Pourcentage de l'énergie consommée placée
> * Clé : Pourcentage_energie_consommee_placee
> * Id : 45244

### Calcul du cumul de l'énergie autoconsommée

- Objectif de calcul : On cherche à calculer l'énergie produite et consommée sur le territoire. Cela correspond au numérateur de la formule de l'autoconsommation qui est Énergie produite et consommée sur le territoire / Énergie produite sur le territoire.

- Source(s) de données :  indicateur Zabbix de clé Energie_autoconsommee et d'id 45245, indicateur Zabbix de clé  Panel_Prod_puissance_mae et d'id 44969, indicateur Zabbix de clé equilibre_general_p_c et d'id 42883

- Méthode de calcul :
> 1. Pour que le calcul soit plus optimisé, on commence par récupérer la dernière valeur enregistrée sur l'indicateur Energie_autoconsommee. Pour la première valeur, le script est lancé avec un autre code qui ne dépend pas de la dernière valeur (on peut le retrouver dans le main, il s'agit de la fonction cumul_enr_autoconso()). Cela permet de ne pas avoir à tout recalculer à chaque fois, on prend simplement la dernière valeur et on ajoute l'énergie produite et consommée sur le territoire dans les 15 dernières minutes.
> 2. Pour calculer l'énergie produite et consommée sur le territoire dans les 15 dernières minutes, on va prendre l'énergie produite sur le territoire mise à l'échelle du panel, et lui enlever ce qui a été exporté. Pour la production, on additionne simplement les valeurs sur les dernières 24 heures de l'indicateur Zabbix Panel_Prod_puissance_mae (en convertissant en énergie).
> 3. Puis on calcule l'énergie exportée pour la soustraire. Pour cela, on fait la somme de tout ce qui est au-dessus de 0 sur le graphique de l'équilibre (en convertissant en énergie), c'est-à-dire sur l'indicateur Zabbix equilibre_general_p_c.
> 4. Enfin, on agrège tout en faisant 1. + (2. - 3.).

- Indicateur Zabbix correspondant : 
> * Nom : Énergie autoconsommée sur le territoire
> * Clé : Energie_autoconsommee
> * Id : 45245

### Calcul du pourcentage d'autoconsommation du territoire sur 30 jours

- Objectif de calcul : On cherche à calculer ici le taux d'autoconsommation du territoire mis sous forme de pourcentage. La formule du taux d'autoconsommation est toujours Énergie produite et consommée sur le territoire / Énergie produite sur le territoire, et on la suit cette fois-ci en entier.

- Source(s) de données : indicateur Zabbix de clé  Panel_Prod_puissance_mae et d'id 44969, indicateur Zabbix de clé equilibre_general_p_c et d'id 42883

- Méthode de calcul (explication du SQL) : 
> 1. On commence par calculer le numérateur de la fraction qui est l'énergie produite et consommée sur le territoire. On applique exactement la même méthode que pour l'indicateur précédent, c'est-à-dire qu'on soustrait le surplus de production à la production d'énergie mise à l'échelle. La seule différence ici est qu'on s'en tient au dernier mois.
> 2. Puis on calcule le dénominateur qui correspond à l'énergie produite sur le territoire le mois dernier.

- Indicateur Zabbix correspondant : 
> * Nom : Pourcentage d'autoconsommation du territoire
> * Clé : Pourcentage_autoconsommation
> * Id : 45246

### Calcul de l'énergie produite par filière

- Objectif de calcul : On cherche à calculer l'énergie (en Wh) produite sur le territoire par filière. C'est-à-dire qu'on a une fonction par filière avec seulement la source de données et l'indicateur de sortie qui change.

- Source(s) de données éolien : indicateur Zabbix de clé Prod_eolienne et d'id 45197
- Source(s) de données solaire : indicateur Zabbix de clé Prod_solaire et d'id 45198
- Source(s) de données méthanisation : indicateur Zabbix de clé Prod_methanisation et d'id 45248

- Méthode de calcul : La finalité est un graphique et le service est appelé toutes les 15 minutes. Puisqu'on prend ici des puissances (dans les sources de données), on ne s'intéresse qu'à la production des 15 dernières minutes. Donc pour chaque filière, on additionne les puissances de production des 15 dernières minutes, sachant que une valeur de production est reçue toutes les minutes.

- Indicateur Zabbix correspondant éolien : 
> * Nom : Énergie éolienne
> * Clé : Enr_eolienne
> * Id : 45257
- Indicateur Zabbix correspondant solaire : 
> * Nom : Énergie solaire
> * Clé : Enr_solaire
> * Id : 45259
- Indicateur Zabbix correspondant méthanisation : 
> * Nom : Énergie méthanisation
> * Clé : Enr_methanisation
> * Id : 45262

### Calcul de la part de chaque filière dans la production actuelle

- Objectif de calcul : On cherche à calculer la part que représente chaque filière dans la production totale du territoire. On veut une valeur la plus actuelle possible donc on se concentre sur les 15 dernières minutes. Comme pour l'indicateur précédent, on a une fonction par filière avec seulement la source de données et l'indicateur de sortie qui change.

- Source(s) de données éolien : indicateur Zabbix de clé Prod_eolienne et d'id 45197
- Source(s) de données solaire : indicateur Zabbix de clé Prod_solaire et d'id 45198
- Source(s) de données méthanisation : indicateur Zabbix de clé Prod_methanisation et d'id 45248

- Méthode de calcul : Pour notre pourcentage, on a besoin de deux valeurs : la production d'énergie totale, et la production de la filière qu'on regarde. C'est pourquoi dans chaque cas on parcourt les trois indicateurs de production (correspondant à chaque filière). On agrège deux indicateurs : la production totale (prod_enr) dans laquelle on ajoute toutes les valeurs des 15 dernières minutes des trois indicateurs, et la puissance de la filière concernée (puissance_\<filière\>) où on ne met que les valeurs de la filière qu'on regarde. Enfin, on calcule le pourcentage correspondant à la puissance de la filière divisée par la production totale.

- Indicateur Zabbix correspondant éolien : 
> * Nom : Part de l'éolien dans la production
> * Clé : Part_eolien_prod
> * Id : 45251
- Indicateur Zabbix correspondant solaire : 
> * Nom : Part du solaire dans la production
> * Clé : Part_solaire_prod
> * Id : 45252
- Indicateur Zabbix correspondant méthanisation : 
> * Nom : Part de la métha dans la production
> * Clé : Part_metha_prod
> * Id : 45253

***

## Encapsulation dans un fichier .csv

Librairies utilisées : **os**, **pandas**

- On commence par créer et ouvrir le fichier .csv s'il n'existe pas déjà. On récupère le path courant pour mettre le fichier créé au même endroit, et on lui choisit un nom : c'est indics.csv pour la pré-production, et indics-prod.csv pour la production. On agrège ensuite ces deux données dans la variable finalpath grâce à la fonction join qui met les bons séparateurs ("/" ou "\") selon les systèmes d'exploitation. Enfin, on ouvre le fichier en écriture.

- Puis, la procédure suivie est la même pour chaque indicateur. On crée une variable dans laquelle on met le résultat de la fonction qui calcule l'indicateur. On met ensuite ce nombre dans un DataFrame avant de le convertir en string en ne prenant que la valeur qui nous intéresse. Enfin, on écrit la ligne correspondante à l'indicateur dans le fichier .csv sous la forme imposée par Zabbix soit "Hôte Clé Valeur".

## Connexion et envoie au serveur

### Connexion au serveur

Utilisation des librairies suivantes : 

Pour se connecter au serveur, on crée un objet ConnectionZabbix en faisant appel à la classe correspondante. Il faut fournir au constructeur l'ip du serveur et le nom de l'hôte. Cet objet dispose d'un attribut "Measurements" qui est un tableau de Measurement initialisé vide dans lequel on va ajouter les mesures les unes après les autres.

### Ajout des différentes mesures

Pour chaque indicateur dans le .csv, on crée un Measurement avec la valeur en string, puis on l'ajoute au tableau de Measurements de l'objet ConnectionZabbix crée.

### Envoi des mesures

Utilisation de la librairie **asyncio**

Enfin, on envoie le tableau Measurements au serveur Zabbix à l'aide de la fonction response(). Il s'agit d'une fonction asynchrone qui nécessite que le main soit définit comme tel (async def), et appelé en conséquence (asyncio.run).

***

## Automatisation et déploiement sur le serveur

Automatiser un script sur un serveur nécessite l'ajout de deux fichiers : un .service et un .timer. Il faudra aussi se connecter en ssh au serveur à l'aide d'un terminal.

1. Il faut donc tout d'abord créer les fichiers .timer et .service qui doivent avoir le même nom dans le projet. Le .service appelle le script à lancer (ici prod.py), et le .timer appelle le service à intervalles de temps réguliers. Dans le .service, il faut préciser le nom du timer et vice-versa, respectivement dans les variables *Wants* et *Requires*. Il faut également indiquer dans le .service le chemin vers le script à exécuter dans la variable *Environment*, et le chemin vers Python dans *ExecStart*. Dans le timer, il faut simplement indiquer l'intervalle de temps auquel on veut qu'il appelle le service dans *OnCalendar*. Ne pas oublier de push quand c'est fait.
2. Puis, de manière très simple, on peut commencer par se connecter au serveur via le gestionnaire de fichiers. Pour cela, il faut cliquer sur "Se connecter à un serveur" dans l'onglet Fichier du navigateur de fichiers de l'ordinateur. On peut ainsi repérer où on veut mettre notre script, créer les dossiers nécessaires. Il faut aussi vérifier que Python est bien installé, sinon il faudra le faire.
3. On se connecte ensuite au serveur distant en ssh à l'aide de la commande ssh user@host, ce qui donne dans notre cas ssh indicateurs@192.168.30.100 à saisir dans un terminal.
4. Dans ce terminal, on peut se placer à l'endroit voulu du projet grâce à des *cd*, puis cloner le projet avec un *git clone*.
5. À cette étape, installer Python sur le serveur s'il n'y est pas déjà, ainsi que tous les modules nécessaires au fonctionnement du code : il faut faire des *pip install* pour chaque import précisé en haut du script.
6. Dans le terminal, se placer à /etc/systemd/system\, si besoin précédé d'un *sudo su* pour passer en administrateur.
7. Y copier les fichiers .service et .timer grâce à la commande suivante : scp -p <chemin source> <chemin destination>, ce qui donne dans notre cas : scp -p /home/indicateurs/Indicateurs-ELFE/indicateurs/indicateurs.timer /etc/systemd/system
8. Faire (sudo) systemctl enable indicateurs.timer pour lancer le timer.
9. Il faut également démarrer le service avec *systemctl start indicateurs.service*.
10. Pour vérifier que ça fonctionne bien, on peut exécuter la commande suivante : *systemctl status indicateurs.service*. Par ailleurs, on peut voir tous les timers qui tournent sur le serveur à l'aide de *systemctl status \*timer*, ou l'état d'un seul timer avec par exemple *systemctl status indicateurs.timer*.

## Piste d'amélioration et suite du projet

- Recalculer le 1er cumul de l'énergie avec la fonction du pourcentage d'après (en faisant pc_with - pc_without) --> voir avec Elias
- Relire / Compléter / Refaire doc

- Rajouter du texte en gras pour guider l'utilisateur dans les points information.
- Vérifier la correspondance des identifiants Zabbix entre la préprod et la prod sur Viriya.
- Pour les graphiques, la lib js ne permet de récupérer que 5000 points (on peut techniquement faire plus, mais cela serait encore plus long à charger). Pour les graphiques, il serait donc peut-être pertinent de créer de nouveaux indicateurs Zabbix qui ne récupère qu'une donnée sur 96 de l'indicateur de base pour avoir une valeur par 24 heures par exemple. Il faudrait dans ce cas remplacer les indicateurs présentés sur le tableur de Cédric.
- Les indicateurs de cumul recalculent à chaque fois tout, il serait donc beaucoup plus optimal d'opter pour une autre méthode de calcul en récupérant la valeur précédente et en ajoutant simplement ce qui a été placé depuis.