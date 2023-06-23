# Indicateurs-ELFE

## Procédure de déploiement sur le serveur

1. Pour voir les timers qui tournent déjà sur le système, on peut faire systemctl status *timer
2. Dans un terminal, se placer à /etc/systemd/system\
Cela nécessite peut-être d'être en root donc faire sudo su avant
3. Y copier les fichiers X.service et X.timer en utilisant sudo et scp\
La commande est : scp [nom d'utilisateur source@IP]:/[dossier et nom de fichier] [nom d'utilisateur de destination@IP]:/[dossier de destination]\
Dans le cas où la source ou la destination est locale, on peut juste indiquer le chemin./
On peut y faire des modifications notamment les descriptions, les variables d'environnement du X.service et le OnCalendar du X.timer. De plus les deux doivent s'entre-référencer via leurs paramètres respectifs Wants et Requires.
4. Faire sudo systemd enable X.timer pour le lancer
5. Pour vérifier si ça fonctionne, on peut refaire systemctl status *timer

Manque un git clone car on arrive sur un serveur vide