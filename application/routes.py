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
        "SELECT fname, lname FROM BankUser WHERE UserID = %s", (currentuser[UserColumn.UID.value],))
    user = db_cursor.fetchall()
    db_cursor.execute(
        "SELECT * FROM BankAccount WHERE UserID = %s ORDER BY accname DESC", (currentuser[UserColumn.UID.value],))
    account_rows = db_cursor.fetchall()
    length = len(account_rows)
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
    # this query groups the tables by different bank accounts owned by the current user
    #
    db_cursor.execute(
        "SELECT accnum FROM BankAccount WHERE UserID = %s ORDER BY accname DESC", (currentuser[UserColumn.UID.value],))
    account_tuples = db_cursor.fetchall()
    last_transaction = []
    for account in account_tuples:
        db_cursor.execute(
            "SELECT amount, timestamp, type FROM Transaction WHERE accnum=%s  ORDER BY timestamp DESC LIMIT 1", (account[0],))
        transact = db_cursor.fetchall()
        db_cursor.execute(
            "SELECT amount, timestamp, type || 'from' FROM Transaction NATURAL JOIN Transfer WHERE destination=%s ORDER BY timestamp DESC LIMIT 1", (account[0],))
        incoming_transfer = db_cursor.fetchall()
        if transact and incoming_transfer and transact[0][1] < incoming_transfer[0][1]:
            last_transaction.append(incoming_transfer[0])
        elif transact and incoming_transfer and transact[0][1] > incoming_transfer[0][1]:
            last_transaction.append(transact[0])
        else:
            if transact:
                last_transaction.append(transact[0])
            elif incoming_transfer:
                last_transaction.append(incoming_transfer[0])
            else:
                last_transaction.append([])

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
        db_cursor.execute("SELECT * FROM BankUser WHERE email = %s", (email,))
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
        db_cursor.execute("SELECT * FROM BankUser WHERE UserID = %s", (id,))
        session["user_id"] = db_cursor.fetchall()[UserColumn.UID.value]
        # still need to set up flash messages
        flash("user created")
        return redirect('/')

    else:
        return render_template("register.html")


@ app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        email = request.form.get("email")
        pw = request.form.get("password")
        db_cursor.execute("SELECT * FROM BankUser WHERE Email = %s", (email,))
        user = db_cursor.fetchall()
        # check email is in database and input password matches the hashed password stored
        if not (user and bcrypt.check_password_hash(user[0][UserColumn.PWHASH.value], pw)):
            return render_template("error.html", error_text="Wrong credentials.")
        else:
            # store logged in user as current user
            session["user_id"] = user[UserColumn.UID.value]
            return redirect("/")
    else:
        return render_template("login.html")


@ app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/login")


@ app.route("/createaccount", methods=["GET", "POST"])
@ requirelogin
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


@ app.route("/deposit", methods=["GET", "POST"])
@ requirelogin
def deposit():
    if request.method == "POST":
        amount = request.form.get("amount")
        if float(amount) < 0:
            return render_template('error.html', error_text="Transaction amount must be greater than 0")
        transaction_id = uuid.uuid4().int & (1 << 30)-1
        timestamp = datetime.now()
        accNum = session["accNum"]
        db_cursor.execute(
            "SELECT balance FROM BankAccount WHERE accNum = %s", (accNum,))
        acc_bal = db_cursor.fetchall()[0][0]
        db_cursor.execute("INSERT INTO Transaction(transactionID, type, amount, timestamp, accnum) VALUES (%s, %s, %s, %s, %s)",
                          (transaction_id, "deposit", amount, timestamp, accNum))

        db_cursor.execute(
            "UPDATE BankAccount SET balance = %s + %s WHERE AccNum = %s", (acc_bal, amount, accNum,))
        db_connection.commit()
        return redirect('/')
    else:
        return render_template('deposit.html')


@ app.route("/withdraw", methods=["GET", "POST"])
@ requirelogin
def withdraw():
    if request.method == "POST":
        amount = request.form.get("amount")
        if float(amount) < 0:
            return render_template('error.html', error_text="Transaction amount must be greater than 0")
        transaction_id = uuid.uuid4().int & (1 << 30)-1
        timestamp = datetime.now()
        accNum = session["accNum"]
        db_cursor.execute(
            "SELECT balance FROM BankAccount WHERE accNum = %s", (accNum,))
        acc_bal = db_cursor.fetchall()[0][0]

        # make sure current balance is enough to withdraw the requested amount
        if float(amount) <= acc_bal:
            db_cursor.execute("INSERT INTO Transaction(transactionID, type, amount, timestamp, accnum) VALUES (%s, %s, %s, %s, %s)",
                              (transaction_id, "withdraw", amount, timestamp, accNum))
            db_cursor.execute(
                "UPDATE BankAccount SET balance = %s - %s WHERE AccNum = %s", (acc_bal, amount, accNum,))
            db_connection.commit()
        else:
            return render_template('error.html', error_text="Can't withdraw more than current balance :,( ")

        return redirect('/')
    else:
        return render_template('withdraw.html')


@ app.route("/transfer", methods=["GET", "POST"])
@ requirelogin
def transfer():
    # this method decreases the balance in the source account (get it from current account stored in session)
    # and increases it in destination account (get it from form in template)
    # it also stores a new entry in transaction table as well as in transfer table (similar to withdraw and deposit)
    if request.method == "POST":
        amount = request.form.get("amount")
        if float(amount) < 0:
            return render_template('error.html', error_text="Transaction amount must be greater than 0")
        transaction_id = uuid.uuid4().int & (1 << 30)-1
        timestamp = datetime.now()
        accNum = session["accNum"]
        db_cursor.execute(
            "SELECT balance FROM BankAccount WHERE accNum = %s", (accNum,))
        acc_bal = db_cursor.fetchall()[0][0]

        destination_acc = request.form.get("destination")  # destination
        if destination_acc == accNum:
            return render_template('error.html', error_text="Cannot transfer to same account")
        if not destination_acc:  # {destination_acc}
            return render_template('error.html', error_text="Need to provide a destination account")
        db_cursor.execute(
            "SELECT * from BankAccount WHERE AccNum = %s", (destination_acc,))  # destination acct number
        if not db_cursor.fetchall():
            return render_template('error.html', error_text="Can't transfer to an account that doesn't exist")
        db_cursor.execute(
            "SELECT balance FROM BankAccount WHERE accNum = %s", (destination_acc,))
        second_acct_bal = db_cursor.fetchall()[0][0]
        # make sure current balance is enough to transfer the requested amount
        if float(amount) <= acc_bal:
            db_cursor.execute("INSERT INTO Transaction(transactionID, type, amount, timestamp, accnum) VALUES (%s, %s, %s, %s, %s)",
                              (transaction_id, "transfer", amount, timestamp, accNum))
            db_cursor.execute(
                "INSERT INTO Transfer (transactionID, destination) VALUES (%s, %s)", (transaction_id, destination_acc))
            db_cursor.execute(  # {accNum}
                "UPDATE BankAccount SET balance = %s - %s WHERE accnum = %s", (acc_bal, amount, accNum,))
            db_cursor.execute(
                "UPDATE BankAccount SET balance = %s + %s WHERE accnum = %s", (second_acct_bal, amount, destination_acc,))
            db_connection.commit()
        else:
            return render_template('error.html', error_text="Can't withdraw more than current balance.")
        return redirect('/')
    else:
        return render_template('transfer.html')


@ app.route("/history", methods=["GET", "POST"])
@ requirelogin
def history():
    # all transactions made by current user for all of their accounts
    user = session["user_id"]
    db_cursor.execute(
        "SELECT accname, type, amount, timestamp FROM Transaction NATURAL JOIN BankAccount WHERE UserID = %s ORDER BY timestamp DESC", (user[0],))
    transaction_rows = db_cursor.fetchall()
    return render_template('history.html', transaction_rows=transaction_rows, user=user[2].capitalize() + " " + user[3].capitalize())


@ app.route("/account", methods=["GET", "POST"])
@ requirelogin
def account():
    accNum = request.args.get('accNum')
    session["accNum"] = accNum
    db_cursor.execute(
        "SELECT balance FROM BankAccount WHERE accnum = %s", (accNum,))
    bal = db_cursor.fetchall()
    bal = ("{:.2f}".format(bal[0][0]))
    db_cursor.execute(
        "SELECT transaction.transactionid, type, amount, timestamp, accnum, destination FROM transaction LEFT JOIN transfer ON transaction.transactionid = transfer.transactionid WHERE AccNum = %s", (accNum,))
    transaction_history = db_cursor.fetchall()
    db_cursor.execute(
        "SELECT transaction.transactionid, type || ' from', amount, timestamp, accnum, destination FROM transaction LEFT JOIN transfer ON transaction.transactionid = transfer.transactionid WHERE destination = %s", (accNum,))
    for tuple in db_cursor.fetchall():
        transaction_history.append(tuple)
    transaction_history.reverse()
    return render_template('account.html', accNum=accNum, bal=bal, transaction_rows=transaction_history)
