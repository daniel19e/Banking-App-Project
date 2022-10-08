from flask import Flask, flash, redirect, render_template, request, session
from flask_bcrypt import Bcrypt
import os
import psycopg2
from tempfile import mkdtemp
from flask_session import Session


app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'vzj9ew5aeuqf5m19'
SESSION_TYPE = 'redis'
app.config.from_object(__name__)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

conn = psycopg2.connect(
    host="localhost",
    database="bankapp",
    user="Daniel",  # need to setup environment variable
    password="Karma010119")  # need to setup environment variable

# Open a cursor to perform database operations
dbcur = conn.cursor()
