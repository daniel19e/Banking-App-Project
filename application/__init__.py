from flask import Flask, flash, redirect, render_template, request, session
from flask_bcrypt import Bcrypt
import os
import psycopg2
from flask.ext.session import Session


app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'vzj9ew5aeuqf5m19'
SESSION_TYPE = 'redis'
app.config.from_object(__name__)
Session(app)

conn = psycopg2.connect(
    host="localhost",
    database="bankapp",
    user=os.getenv('dbusername'),  # need to setup environment variable
    password=os.getenv('dbpassword'))  # need to setup environment variable

# Open a cursor to perform database operations
dbcur = conn.cursor()
