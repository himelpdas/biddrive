chown -R root:root *.py
chown -R root:root gluon
chown -R root:root scripts
chown -R root:root applications/*/modules/
chown -R root:root applications/*/models/
chown -R root:root applications/*/controllers/
chown -R root:root applications/*/views/
chown -R root:root applications/*/static/
chown -R root:root applications/*/cron/

echo "unlock with chown -R www-data:www-data ./"