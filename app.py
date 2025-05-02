from flask import Flask
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
mysql = MySQL(app)


from airline_routes import *
from airport_routes import *
from flight_routes import *
from booking_routes import *

if __name__ == '__main__':
    
    app.run(debug=True)