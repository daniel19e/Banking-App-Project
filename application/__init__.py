from flask import Flask, flash, redirect, render_template, request, session
from flask_bcrypt import Bcrypt
import os
import psycopg2


app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'vzj9ew5aeuqf5m19'


db_connection = psycopg2.connect(
    host="localhost",
    database="lore",
    user="lore",  # need to setup environment variable
    password="1234")  # need to setup environment variable

# Open a cursor to perform database operations
db_cursor = db_connection.cursor()
