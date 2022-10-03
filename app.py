from flask import Flask, flash, redirect, render_template, request, session

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register")
def register():
    pass


@app.route("/login")
def login():
    pass


@app.route("/deposit")
def deposit():
    pass


@app.route("/withdraw")
def withdraw():
    pass


@app.route("/transfer")
def transfer():
    pass


@app.route("/history")
def history():
    pass
