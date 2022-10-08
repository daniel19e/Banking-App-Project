from flask import flash, redirect, render_template, request, session
from application import app, dbcur, bcrypt, conn
import uuid


@app.route("/")
def index():
    dbcur.execute("SELECT * FROM BankUser")
    user = dbcur.fetchall()
    return render_template("index.html", user=user[0][2] + " " + user[0][3])


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        id = uuid.uuid4().int & (1 << 30)-1
        email = request.form.get("email")
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        dob = request.form.get("dob")
        if request.form.get("password") != request.form.get("pwconfirmation"):
            return redirect('/')
        hashpw = bcrypt.generate_password_hash(request.form.get("password"))
        print("asdasdd", id, email, fname, lname)

        dbcur.execute("INSERT INTO BankUser (UserID, Dob, Fname, Lname, Email, PwHash) VALUES (%s, %s, %s, %s, %s, %s)",
                      (id, dob, fname, lname, email, hashpw))
        conn.commit()
        flash("user created")
        return redirect('/')

    else:
        return render_template("register.html")


@app.route("/login")
def login():
    return render_template("login.html")


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
