read -p "Choose your admin password?" passwd
sudo pip install virtualenv
sudo pip install psycopg2
virtualenv venv --distribute
source venv/bin/activate
pip freeze > requirements.txt
echo "web: python web2py.py -a '$passwd' -i 0.0.0.0 -p \$PORT" > Procfile
git init
git add .
git add Procfile
git commit -a -m "first commit"
heroku create
git push heroku master
heroku scale web=1
heroku open
