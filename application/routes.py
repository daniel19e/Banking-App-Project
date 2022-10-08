from flask import flash, redirect, render_template, request, session
from application import app, dbcur, bcrypt, conn
import uuid
from enum import Enum
from tempfile import mkdtemp
from flask_session import Session
from functools import wraps


SESSION_TYPE = 'redis'
app.config.from_object(__name__)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


class Column(Enum):
    ID = 0
    DOB = 1
    FNAME = 2
    LNAME = 3
    EMAIL = 4
    PWH = 5


def requirelogin(f):
    # we should apply this to all the routes, see index example
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@requirelogin
def index():
    currentuser = session["user_id"]
    dbcur.execute(
        f"SELECT * FROM BankUser WHERE UserID = {currentuser[Column.ID.value]}")
    user = dbcur.fetchall()
    return render_template("index.html", user=user[0][Column.FNAME.value] + " " + user[0][Column.LNAME.value])


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        session.clear()
        id = uuid.uuid4().int & (1 << 30)-1
        email = request.form.get("email")
        dbcur.execute(f"SELECT * FROM BankUser WHERE email = '{email}'")
        if len(dbcur.fetchall()):
            # email already in database
            return render_template('error.html')
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        dob = request.form.get("dob")
        if request.form.get("password") != request.form.get("pwconfirmation"):
            # password doesn't match confirmation field
            return render_template('error.html')

        hashpw = bcrypt.generate_password_hash(
            request.form.get("password")).decode('utf-8')

        # add new user to database
        dbcur.execute("INSERT INTO BankUser (UserID, Dob, Fname, Lname, Email, PwHash) VALUES (%s, %s, %s, %s, %s, %s)",
                      (id, dob, fname, lname, email, hashpw))
        conn.commit()
        dbcur.execute(f"SELECT * FROM BankUser WHERE UserID = {id}")
        session["user_id"] = dbcur.fetchall()[Column.ID.value]
        flash("user created")
        return redirect('/')

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        email = request.form.get("email")
        pw = request.form.get("password")
        dbcur.execute(f"SELECT * FROM BankUser WHERE Email = '{email}'")
        user = dbcur.fetchall()
        print(user)
        if not bcrypt.check_password_hash(user[0][Column.PWH.value], pw):
            return render_template("error.html")
        else:
            print(user)
            session["user_id"] = user[Column.ID.value]
            return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/login")


@ app.route("/deposit")
def deposit():
    pass


@ app.route("/withdraw")
def withdraw():
    pass


@ app.route("/transfer")
def transfer():
    pass


@ app.route("/history")
def history():
    pass
