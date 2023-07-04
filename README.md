# Indicateurs-ELFE

## Calcul du nombre d'appareils connectés par 1/4h

On compte simplement le nombre de lignes correspondant au dernier quart d'heure de la table result, puisqu'il apparaît une ligne par quart d'heure par machine que l'EMS réfléchit à lancer ou non.

## Calcul du pourcentage des appareils de ELFE lancés dans les dernières 24h

1. On calcule d'abord le nombre d'appareils pilotables par l'EMS : on exclue donc les compteurs et les producteurs. Cela servira de base pour faire le pourcentage.
2. On calcule ensuite le nombre de lancement qui ont eu lieu depuis 24h. On garde ensemble les appareils continus et discontinus. Les conditions ici appliquées pour la sélection des appareils à compter sont :
    - decisions_0 = 1 : cela signifie que l'EMS a choisi de lancer l'appareil au prochain quart d'heure. Cependant, cela nous oblige à compter par machine_id distincts puisqu'il arrive souvent que l'appareil ne se lance en fait pas et que la même décision soit reprise au quart d'heure suivant. On part donc du postulat que rares sont les personnes à lancer leur lave-vaisselle trois fois en 24h, et on prent le parti de ne compter qu'une fois par jour les machines fonctionnant en continu.
    - timestamp > (maintenant - 24h) : cela permet de ne garder bien que les appareils lancés dans les dernières 24h.
3. On met enfin le résultat de la fraction des deux (1. / 2.) sous forme de pourcentage, en ne gardant qu'un seul chiffre après la virgule.

## Calcul du cumul des kW d'énergie placés par l'EMS depuis le début du projet

1. 

## Procédure de déploiement sur le serveur

1. Pour voir les timers qui tournent déjà sur le système, on peut faire systemctl status *timer
2. Pour se balader dans l'arborescence du serveur, on peut faire "Se connecter à un serveur" dans l'onglet Fichier du navigateur de fichiers de l'ordinateur
3. Ouvrir un terminal sur le serveur distant en ssh avec la commande : ssh user@host, ce qui donne dans notre cas ssh indicateurs@192.168.30.100
4. Modifier les fichiers indicateurs.service et indicateurs.timer. On peut y modifier notamment les descriptions, les variables d'environnement du X.service et le OnCalendar du X.timer. De plus les deux doivent s'entre-référencer via leurs paramètres respectifs Wants et Requires.
5. En vérifiant qu'on est bien dans /home/indicateurs, faire un git clone du projet entier
6. Dans un terminal, se placer à /etc/systemd/system\
Cela nécessite peut-être d'être en root donc faire sudo su avant
7. Y copier les fichiers indicateurs.service et indicateurs.timer grâce à la commande suivante : scp -p <chemin source> <chemin destination>, ce qui donne dans notre cas : scp -p /home/indicateurs/Indicateurs-ELFE/indicateurs/indicateurs.timer /etc/systemd/system
8. Faire (sudo) systemctl enable indicateurs.timer pour le lancer
9. Pour vérifier si ça fonctionne, on peut refaire systemctl status indicateurs.service
10. Si ça ne fonctionne pas, une piste à explorer est les modules python qui ne sont probablement pas installés sur le serveur. Dans ce cas, faire des pip install à la chaîne.