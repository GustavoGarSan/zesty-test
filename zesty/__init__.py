from flask import Flask
from flask_cors import CORS
from flask_restful import Api
import psycopg2
import os

app = Flask(__name__)

CORS(app)

user = os.environ['POSTGRES_USER']
password = os.environ['POSTGRES_PASSWORD']
host = os.environ['POSTGRES_HOST']
database = os.environ['POSTGRES_DB']
port = os.environ['POSTGRES_PORT']

conn = psycopg2.connect(host=host, port=port, database=database, user=user, password=password)

app.debug = False

# Api
from api.controllers import DisplayApi, FindaApi, StatsApi
api = Api(app)
api.add_resource(DisplayApi, '/display/<string:id>')
api.add_resource(FindaApi, '/find')
api.add_resource(StatsApi, '/statistics/<string:id>')