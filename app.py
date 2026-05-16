from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_file
)

import sqlite3
import datetime
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas


# =========================
# APP CONFIG
# =========================

app = Flask(__name__)
app.secret_key = "smart_expense_secret"


# =========================
# DATABASE CONNECTION
# =========================

def connect_db():
    conn = sqlite3.connect("expense.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# CREATE TABLES
# =========================

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        category TEXT,
        date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS income(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budget(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL
    )
    """)

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(amount) AS total_income FROM income")
    income = cursor.fetchone()["total_income"] or 0

    cursor.execute("SELECT SUM(amount) AS total_expense FROM expenses")
    expense = cursor.fetchone()["total_expense"] or 0

    cursor.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 5")
    recent = cursor.fetchall()

    cursor.execute("SELECT amount FROM budget ORDER BY id DESC LIMIT 1")
    budget_row = cursor.fetchone()
    budget = budget_row["amount"] if budget_row else 0

    conn.close()

    balance = income - expense

    budget_alert = ""
    warning = ""

    if expense > budget:
        budget_alert = "⚠ Budget Exceeded!"

    if expense > income:
        warning = "⚠ Expense greater than income!"

    return render_template(
        "index.html",
        income=income,
        expense=expense,
        balance=balance,
        recent_expenses=recent,
        budget_alert=budget_alert,
        warning=warning
    )


# =========================
# ADD INCOME
# =========================

@app.route("/income", methods=["GET", "POST"])
def income():

    if request.method == "POST":
        amount = float(request.form["amount"])

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO income(amount) VALUES(?)", (amount,))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_income.html")


# =========================
# ADD EXPENSE
# =========================

@app.route("/expense", methods=["GET", "POST"])
def expense():

    if request.method == "POST":
        amount = float(request.form["amount"])
        category = request.form["category"]
        date = str(datetime.date.today())

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO expenses(amount, category, date)
            VALUES(?,?,?)
        """, (amount, category, date))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_expense.html")


# =========================
# HISTORY
# =========================

@app.route("/history")
def history():

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
    expenses = cursor.fetchall()

    conn.close()

    return render_template("history.html", expenses=expenses)


# =========================
# DELETE
# =========================

@app.route("/delete/<int:id>")
def delete(id):

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM expenses WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/history")


# =========================
# CHARTS
# =========================

@app.route("/charts")
def charts():

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT category, amount FROM expenses")
    data = cursor.fetchall()
    conn.close()

    categories = {}

    for i in data:
        cat = i["category"]
        categories[cat] = categories.get(cat, 0) + i["amount"]

    # PIE
    plt.figure()
    plt.pie(categories.values(), labels=categories.keys(), autopct="%1.1f%%")
    plt.title("Expense Pie Chart")
    plt.savefig("static/pie.png")
    plt.close()

    # BAR
    plt.figure()
    plt.bar(categories.keys(), categories.values())
    plt.title("Expense Bar Chart")
    plt.savefig("static/bar.png")
    plt.close()

    return render_template("charts.html")


# =========================
# SEARCH
# =========================

@app.route("/search", methods=["GET", "POST"])
def search():

    results = []

    if request.method == "POST":
        keyword = request.form["keyword"]

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM expenses
            WHERE category LIKE ?
        """, ('%' + keyword + '%',))

        results = cursor.fetchall()
        conn.close()

    return render_template("search.html", results=results)


# =========================
# SIGNUP
# =========================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        if user:
            return "User already exists"

        cursor.execute("""
            INSERT INTO users(username, password)
            VALUES(?,?)
        """, (username, password))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE username=? AND password=?
        """, (username, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/")

        return "Invalid login"

    return render_template("login.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# PDF REPORT (FIXED)
# =========================

@app.route("/report")
def report():

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
    expenses = cursor.fetchall()

    cursor.execute("SELECT SUM(amount) AS total FROM expenses")
    total = cursor.fetchone()["total"] or 0

    conn.close()

    pdf_file = "report.pdf"
    pdf = canvas.Canvas(pdf_file)

    y = 800

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(100, y, "Smart Expense Report")

    y -= 40
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, y, f"Total Expense: {total}")

    y -= 40
    pdf.drawString(100, y, "Expense List:")

    y -= 30

    for e in expenses:
        line = f"{e['date']} | {e['category']} | {e['amount']}"
        pdf.drawString(100, y, line)
        y -= 20

        if y < 100:
            pdf.showPage()
            y = 800

    pdf.save()

    return send_file(pdf_file, as_attachment=True)


# =========================
# RUN
# =========================

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)

