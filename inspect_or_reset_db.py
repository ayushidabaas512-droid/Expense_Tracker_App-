import sqlite3

def check_integrity(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        return result[0]
    except Exception as e:
        return f"Error: {e}"

print(check_integrity("finance_app.db"))

