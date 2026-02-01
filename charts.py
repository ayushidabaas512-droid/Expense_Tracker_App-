import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk

def create_pie_chart(parent, data, labels, title):
    fig, ax = plt.subplots()
    ax.pie(data, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.set_title(title)
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def plot_expenses_pie():
    import sqlite3
    conn = sqlite3.connect("expense_tracker.db")
    cur = conn.cursor()
    cur.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
    data = cur.fetchall()
    if not data:
        print("No expense data to plot.")
        return
    categories, amounts = zip(*data)
    plt.figure(figsize=(6,6))
    plt.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
    plt.title("Expense Breakdown")
    plt.show()

def plot_income_vs_expense():
    import sqlite3
    conn = sqlite3.connect("expense_tracker.db")
    cur = conn.cursor()
    cur.execute("SELECT SUM(amount) FROM income")
    income = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(amount) FROM expenses")
    expense = cur.fetchone()[0] or 0

    plt.figure(figsize=(6,4))
    plt.bar(["Income", "Expenses"], [income, expense], color=["green", "red"])
    plt.title("Income vs Expenses")
    plt.ylabel("Amount")
    plt.show()