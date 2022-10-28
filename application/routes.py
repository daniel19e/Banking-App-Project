from flask import flash, redirect, render_template, request, session
from application import app, db_cursor, bcrypt, db_connection
import uuid
from enum import Enum
from tempfile import mkdtemp
from flask_session import Session
from functools import wraps
from datetime import date, datetime

SESSION_TYPE = 'redis'
app.config.from_object(__name__)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


class UserColumn(Enum):
    UID = 0
    DOB = 1
    FNAME = 2
    LNAME = 3
    EMAIL = 4
    PWHASH = 5

# find some way to not require this, get values directly from select statement


class AccountColumn(Enum):
    ACCNUM = 0
    UID = 1
    ACCTYPE = 2
    ACCNAME = 3
    BAL = 4
    CREATED = 5


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
    # currently, url only shows the current user's name,
    # we want to display the accounts they've created with the respective balances.
    # also, when we click on one particular account it should show history for that account
    currentuser = session["user_id"]
    db_cursor.execute(
        f"SELECT fname, lname FROM BankUser WHERE UserID = {currentuser[UserColumn.UID.value]}")
    user = db_cursor.fetchall()
    db_cursor.execute(
        f"SELECT * FROM BankAccount WHERE UserID = {currentuser[UserColumn.UID.value]} ORDER BY accname DESC")
    account_rows = db_cursor.fetchall()
    length = [x for x in range(len(account_rows))]
    accountID = [account[AccountColumn.ACCNUM.value]
                 for account in account_rows]
    # extracts float from balances dict and formats it to currency notation
    balanceStrings = ["{:.2f}".format(account[AccountColumn.BAL.value])
                      for account in account_rows]
    typeStrings = ["".join(str(account[AccountColumn.ACCTYPE.value])).capitalize()
                   for account in account_rows]
    nameStrings = ["".join(str(account[AccountColumn.ACCNAME.value])).capitalize()
                   for account in account_rows]

    # get last four digits of account number to display
    last_four_digits = [str(x)[-4:] for x in accountID]
    db_cursor.execute(
        f"""SELECT amount, timestamp::date || ' at ' || timestamp::time, type FROM Transaction NATURAL JOIN BankAccount WHERE 
        timestamp IN (SELECT max(timestamp) FROM Transaction NATURAL JOIN BankAccount
        WHERE UserID = {currentuser[UserColumn.UID.value]} GROUP BY accnum) 
        ORDER BY accname DESC""")
    last_transaction = db_cursor.fetchall()

    return render_template("index.html", user=" ".join([x.capitalize() for x in user[0]]),
                           balanceStrings=balanceStrings,
                           nameStrings=nameStrings,
                           length=length,
                           accountID=accountID,
                           typeStrings=typeStrings,
                           last_four_digits=last_four_digits,
                           last_transaction=last_transaction)


@ app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        session.clear()
        id = uuid.uuid4().int & (1 << 30)-1
        email = request.form.get("email")
        db_cursor.execute(f"SELECT * FROM BankUser WHERE email = '{email}'")
        if len(db_cursor.fetchall()):
            # email already in database
            return render_template('error.html', error_text="Email already registered")
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        dob = request.form.get("dob")
        if request.form.get("password") != request.form.get("pwconfirmation"):
            # password doesn't match confirmation field
            return render_template('error.html', error_text="Passwords don't match.")

        hashpw = bcrypt.generate_password_hash(
            request.form.get("password")).decode('utf-8')

        # add new user to database
        db_cursor.execute("INSERT INTO BankUser (UserID, Dob, Fname, Lname, Email, PwHash) VALUES (%s, %s, %s, %s, %s, %s)",
                          (id, dob, fname, lname, email, hashpw))
        db_connection.commit()
        db_cursor.execute(f"SELECT * FROM BankUser WHERE UserID = {id}")
        session["user_id"] = db_cursor.fetchall()[UserColumn.UID.value]
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
        db_cursor.execute(f"SELECT * FROM BankUser WHERE Email = '{email}'")
        user = db_cursor.fetchall()
        # check email is in database and input password matches the hashed password stored
        if not (user and bcrypt.check_password_hash(user[0][UserColumn.PWHASH.value], pw)):
            return render_template("error.html", error_text="Wrong credentials.")
        else:
            session["user_id"] = user[UserColumn.UID.value]
            return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/login")


@app.route("/createaccount", methods=["GET", "POST"])
@requirelogin
def createaccount():
    if request.method == "POST":
        # gets userID from session, account name from text entry and accounttype from btn value in createaccount.html
        sUser = session["user_id"]
        userID = sUser[UserColumn.UID.value]
        accountID = uuid.uuid4().int & (1 << 30)-1
        balance = 0
        accountName = request.form.get("accountname")
        accountType = request.form['accounttype']
        # from datetime
        curDate = date.today()
        db_cursor.execute("INSERT INTO BankAccount (accnum, userid, acctype, accName, balance, creationdate) VALUES (%s, %s, %s, %s, %s, %s)",
                          (accountID, userID, accountType, accountName, balance, curDate))
        db_connection.commit()
        flash("account created")
        return redirect("/")
    else:
        return render_template("createaccount.html")


@app.route("/deposit", methods=["GET", "POST"])
@requirelogin
def deposit():
    if request.method == "POST":
        amount = request.form.get("amount")
        transaction_id = uuid.uuid4().int & (1 << 30)-1
        timestamp = datetime.now()
        accNum = session["accNum"]
        db_cursor.execute(
            f"SELECT balance FROM BankAccount WHERE accNum = {accNum}")
        acc_bal = db_cursor.fetchall()[0][0]
        db_cursor.execute("INSERT INTO Transaction(transactionID, type, amount, timestamp, accnum) VALUES (%s, %s, %s, %s, %s)",
                          (transaction_id, "deposit", amount, timestamp, accNum))

        db_cursor.execute(
            f"UPDATE BankAccount SET balance = {acc_bal} + {amount} WHERE AccNum = {accNum}")
        db_connection.commit()
        return redirect('/')
    else:
        return render_template('deposit.html')


@app.route("/withdraw", methods=["GET", "POST"])
@requirelogin
def withdraw():
    if request.method == "POST":
        amount = request.form.get("amount")
        transaction_id = uuid.uuid4().int & (1 << 30)-1
        timestamp = datetime.now()
        accNum = session["accNum"]
        db_cursor.execute(
            f"SELECT balance FROM BankAccount WHERE accNum = {accNum}")
        acc_bal = db_cursor.fetchall()[0][0]

        if float(amount) <= acc_bal:
            db_cursor.execute("INSERT INTO Transaction(transactionID, type, amount, timestamp, accnum) VALUES (%s, %s, %s, %s, %s)",
                              (transaction_id, "withdraw", amount, timestamp, accNum))
            db_cursor.execute(
                f"UPDATE BankAccount SET balance = {acc_bal} - {amount} WHERE AccNum = {accNum}")
            db_connection.commit()
        else:
            return render_template('error.html', error_text="Can't withdraw more than current balance :,( ")

        return redirect('/')
    else:
        return render_template('withdraw.html')


@app.route("/transfer")
def transfer():
    pass


@app.route("/history", methods=["GET", "POST"])
@requirelogin
def history():
    # all transactions made by current user for all of their accounts
    db_cursor.execute(
        f"SELECT accname, type, amount, timestamp FROM Transaction NATURAL JOIN BankAccount ORDER BY timestamp DESC")
    transaction_rows = db_cursor.fetchall()
    return render_template('history.html', transaction_rows=transaction_rows)


@app.route("/account", methods=["GET", "POST"])
@requirelogin
def account():
    accNum = request.args.get('accNum')
    session["accNum"] = accNum
    db_cursor.execute(
        f"SELECT balance FROM BankAccount WHERE accnum = {accNum}")
    bal = db_cursor.fetchall()
    bal = ("{:.2f}".format(bal[0][0]))
    db_cursor.execute(f"SELECT * FROM transaction WHERE AccNum = {accNum}")
    transaction_history = db_cursor.fetchall()
    transaction_history.reverse()
    return render_template('account.html', accNum=accNum, bal=bal, transaction_rows=transaction_history)
