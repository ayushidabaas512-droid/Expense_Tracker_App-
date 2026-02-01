def generate_expense_report(expenses):
    report = "Expense Report\n----------------\n"
    for expense in expenses:
        report += f"{expense[1]} - ₹{expense[2]} ({expense[3]}) on {expense[4]}\n"
    return report
