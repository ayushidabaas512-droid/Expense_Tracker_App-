import sqlite3

def setup_database():
    """
    Connects to the SQLite database and creates the necessary tables
    if they do not already exist.
    """
    try:
        connector = sqlite3.connect("Expense Tracker.db")
        cursor = connector.cursor()

        # Create ExpenseTracker table
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS ExpenseTracker (
                ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                Date DATETIME,
                Payee TEXT,
                Description TEXT,
                Amount FLOAT,
                ModeOfPayment TEXT,
                Category TEXT,
                Tags TEXT
            )'''
        )

        # Create Budget Table
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS Budgets (
                ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                Category TEXT NOT NULL,
                Amount FLOAT NOT NULL,
                Period TEXT NOT NULL UNIQUE -- e.g., "YYYY-MM" for monthly budgets
            )'''
        )
        connector.commit()
        print("Database tables checked/created successfully.")
    except sqlite3.Error as e:
        print(f"Error setting up database: {e}")
    finally:
        if connector:
            connector.close()

if __name__ == "__main__":
    setup_database()
