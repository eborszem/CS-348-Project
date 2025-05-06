from flask import Flask
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()
CORS(app)

app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
mysql = MySQL(app)

from index import *
from routes.airline_routes import *
from routes.airport_routes import *
from routes.flight_routes import *
from routes.booking_routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)