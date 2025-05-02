from flask import Flask
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
mysql = MySQL(app)

from index import *

if __name__ == '__main__':
    app.run(debug=True)