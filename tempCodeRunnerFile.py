from flask import Flask, render_template, request, redirect
import json
import datetime
import matplotlib.pyplot as plt

app = Flask(__name__)

file = "expense_data.json"


# ---------- LOAD DATA ----------
def load():

    try:

        with open(file, "r") as f:

            return json.load(f)

    except:

        return {
            "income": 0,
            "expenses": []
        }


# ---------- SAVE DATA ----------
def save(data):

    with open(file, "w") as f:

        json.dump(data, f, indent=4)


# ---------- HOME PAGE ----------
@app.route("/")
def home():

    data = load()

    total_expense = sum(
        item["amount"]
        for item in data["expenses"]
    )

    current_balance = (
        data["income"] - total_expense
    )

    # RECENT TRANSACTIONS
    recent_expenses = (
        data["expenses"][-5:]
    )[::-1]

    # BUDGET ALERT
    budget_alert = ""

    if total_expense > data["budget"]:

        budget_alert = (
            "⚠ Budget Exceeded!"
        )
        warning = ""

        if total_expense > data["income"]:

         warning = "⚠ Expenses exceeded income!"

    return render_template(
        "index.html",
        income=data["income"],
        expense=total_expense,
        balance=current_balance,
        recent_expenses=recent_expenses,
        budget_alert=budget_alert,
        warning=warning
    )


# ---------- ADD INCOME ----------
@app.route("/income", methods=["GET", "POST"])
def income():

    data = load()

    if request.method == "POST":

        amount = float(
            request.form["amount"]
        )

        data["income"] += amount

        save(data)

        return redirect("/")

    return render_template(
        "add_income.html"
    )


# ---------- ADD EXPENSE ----------
@app.route("/expense", methods=["GET", "POST"])
def expense():

    data = load()

    if request.method == "POST":

        amount = float(
            request.form["amount"]
        )

        category = request.form["category"]

        data["expenses"].append({

            "amount": amount,

            "category": category,

            "date": str(
                datetime.date.today()
            )

        })

        save(data)

        return redirect("/")

    return render_template(
        "add_expense.html"
    )


# ---------- BALANCE PAGE ----------
@app.route("/balance")
def balance():

    data = load()

    total_expense = sum(
        item["amount"]
        for item in data["expenses"]
    )

    current_balance = (
        data["income"] - total_expense
    )

    return render_template(
        "balance.html",
        income=data["income"],
        expense=total_expense,
        balance=current_balance
    )


# ---------- HISTORY PAGE ----------
@app.route("/history")
def history():

    data = load()

    return render_template(
        "history.html",
        expenses=data["expenses"]
    )

# ---------- DELETE EXPENSE ----------
@app.route("/delete/<int:index>")
def delete(index):

    data = load()

    if index < len(data["expenses"]):

        data["expenses"].pop(index)

        save(data)

    return redirect("/history")

# ---------- CHART PAGE ----------
@app.route("/charts")
def charts():

    data = load()

    categories = {}

    for item in data["expenses"]:

        cat = item["category"]

        categories[cat] = (
            categories.get(cat, 0)
            + item["amount"]
        )

    # PIE CHART
    plt.figure(figsize=(6, 6))

    plt.pie(
        categories.values(),
        labels=categories.keys(),
        autopct='%1.1f%%'
    )

    plt.title("Expense Distribution")

    plt.savefig("static/pie_chart.png")

    plt.close()

    # BAR CHART
    plt.figure(figsize=(7, 5))

    plt.bar(
        categories.keys(),
        categories.values(),
        color="skyblue"
    )

    plt.title("Category Wise Expenses")

    plt.xlabel("Category")

    plt.ylabel("Amount")

    plt.savefig("static/bar_chart.png")

    plt.close()

    return render_template(
        "charts.html"
    )

# ---------- SEARCH PAGE ----------
@app.route("/search", methods=["GET", "POST"])
def search():

    data = load()

    results = []

    if request.method == "POST":

        keyword = request.form["keyword"]

        results = [

            item for item
            in data["expenses"]

            if keyword.lower()
            in item["category"].lower()

        ]

    return render_template(
        "search.html",
        results=results
    )

# ---------- RUN APP ----------
if __name__ == "__main__":

    app.run(debug=True)