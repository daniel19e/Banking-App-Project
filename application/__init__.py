from flask import Flask, flash, redirect, render_template, request, session
from flask_bcrypt import Bcrypt
import os
import psycopg2

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'vzj9ew5aeuqf5m19'


conn = psycopg2.connect(
    host="localhost",
    database="bankapp",
    user="Daniel",
    password="Karma010119")

# Open a cursor to perform database operations
dbcur = conn.cursor()
