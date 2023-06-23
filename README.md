# Indicateurs-ELFE

## Procédure de déploiement sur le serveur

1. Pour voir les timers qui tournent déjà sur le système, on peut faire systemctl status *timer
2. On peut se balader dans l'arborescence du serveur, on peut faire "Se connecter à un serveur" dans l'onglet Fichier du navigateur de fichiers de l'ordinateur
3. Ouvrir un terminal sur le serveur distant en ssh avec la commande : ssh user@host, ce qui donne dans notre cas ssh indicateurs@192.168.30.100
4. Modifier les fichiers indicateurs.service et indicateurs.timer. On peut y modifier notamment les descriptions, les variables d'environnement du X.service et le OnCalendar du X.timer. De plus les deux doivent s'entre-référencer via leurs paramètres respectifs Wants et Requires.
5. En vérifiant qu'on est bien dans /home/indicateurs, faire un git clone
6. Dans un terminal, se placer à /etc/systemd/system\
Cela nécessite peut-être d'être en root donc faire sudo su avant
7. Y copier les fichiers indicateurs.service et indicateurs.timer grâce à la commande suivante : scp -p <chemin source> <chemin destination>, ce qui donne dans notre cas : scp -p /home/indicateurs/Indicateurs-ELFE/indicateurs/indicateurs.timer /etc/systemd/system
8. Faire sudo systemd enable indicateurs.timer pour le lancer
5. Pour vérifier si ça fonctionne, on peut refaire systemctl status *timer

Manque un git clone car on arrive sur un serveur vide