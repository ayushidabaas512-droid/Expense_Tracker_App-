import tkinter as tk
from tkinter import messagebox, font, ttk
import sqlite3
import hashlib
import colorsys
import json
import os
import time  # Import the time module

# --- Constants ---
DB_NAME = "expense_tracker.db"
THEME_FILE = "theme_pref.json"
DEFAULT_FONT = "Segoe UI"  # Default font
LABEL_FONT_SIZE = 11
ENTRY_FONT_SIZE = 11
BUTTON_FONT_SIZE = 11
HEADING_FONT = "Arial Black"
HEADING_FONT_SIZE = 20
GRADIENT_ANIMATION_SPEED = 100
GRADIENT_LINES = 100
DEFAULT_GRADIENT_COLORS = [(255, 192, 203), (135, 206, 250)]

# --- Global Variables ---
is_dark_mode = False
gradient_canvas = None
gradient_colors = DEFAULT_GRADIENT_COLORS
root = None

# --- Helper Functions ---
def get_database_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)  # Add a timeout
        return conn
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to connect to the database: {e}")
        if conn:
            conn.close()
        return None

def execute_query(conn, query, params=()):
    cursor = None
    try:
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute(query, params)
        if query.lower().startswith("insert") or query.lower().startswith("update") or query.lower().startswith("delete"):
            conn.commit()
        return cursor
    except Exception as e:
        messagebox.showerror("Database Error", f"Error executing query: {e}")
        if cursor:
            cursor.close()
        if conn:
            conn.rollback()
        return None

def fetch_one(cursor):
    try:
        if cursor is None:
            return None
        return cursor.fetchone()
    except Exception as e:
        messagebox.showerror("Database Error", f"Error fetching data: {e}")
        return None

def fetch_all(cursor):
    try:
        if cursor is None:
            return []
        return cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Error fetching data: {e}")
        return []

# --- Password Hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Theme Preference ---
def save_theme_preference():
    try:
        with open(THEME_FILE, "w") as f:
            json.dump({"dark_mode": is_dark_mode}, f)
    except Exception as e:
        print(f"Error saving theme preference: {e}")

def load_theme_preference():
    global is_dark_mode
    try:
        if os.path.exists(THEME_FILE):
            with open(THEME_FILE, "r") as f:
                try:
                    data = json.load(f)
                    is_dark_mode = data.get("dark_mode", False)
                except json.JSONDecodeError:
                    print("Theme file was corrupted.  Resetting to default theme.")
                    is_dark_mode = False
    except Exception as e:
        print(f"Error loading theme preference: {e}")
        is_dark_mode = False

# --- Gradient Drawing ---
def create_gradient_canvas(root):
    global gradient_canvas
    gradient_canvas = tk.Canvas(root, highlightthickness=0)
    gradient_canvas.place(x=0, y=0, relwidth=1, relheight=1)

def draw_gradient(root):
    global gradient_canvas
    if gradient_canvas:
        gradient_canvas.delete("all")
        width = root.winfo_width()
        height = root.winfo_height()
        r1, g1, b1 = gradient_colors[0]
        r2, g2, b2 = gradient_colors[1]

        for i in range(GRADIENT_LINES):
            r = int(r1 + (r2 - r1) * i / GRADIENT_LINES)
            g = int(g1 + (g2 - g1) * i / GRADIENT_LINES)
            b = int(b1 + (b2 - b1) * i / GRADIENT_LINES)
            color = f'#{r:02x}{g:02x}{b:02x}'
            y1 = int(i * height / GRADIENT_LINES)
            y2 = int((i + 1) * height / GRADIENT_LINES)
            gradient_canvas.create_rectangle(0, y1, width, y2, outline="", fill=color)

def animate_gradient(root, step=0):
    global gradient_colors
    h1 = (step % 360) / 360
    h2 = ((step + 60) % 360) / 360
    r1, g1, b1 = [int(x * 255) for x in colorsys.hsv_to_rgb(h1, 0.4, 1)]
    r2, g2, b2 = [int(x * 255) for x in colorsys.hsv_to_rgb(h2, 0.4, 1)]
    gradient_colors[0] = (r1, g1, b1)
    gradient_colors[1] = (r2, g2, b2)
    if not is_dark_mode and gradient_canvas:
        draw_gradient(root)
    root.after(GRADIENT_ANIMATION_SPEED, lambda: animate_gradient(root, step + 1))

def toggle_theme(root):
    global is_dark_mode
    is_dark_mode = not is_dark_mode
    save_theme_preference()
    apply_theme(root)

def apply_theme(root):
    global gradient_canvas
    bg = "#2E2E2E" if is_dark_mode else "#FFFFFF"
    fg = "#FFFFFF" if is_dark_mode else "#000000"
    btn_bg = "#444" if is_dark_mode else "#E0E0E0"
    btn_hover_bg = "#666" if is_dark_mode else "#C0C0C0"
    label_fg = "#DDD" if is_dark_mode else "#555"  # for labels

    root.configure(bg=bg)

    if gradient_canvas:
        if is_dark_mode:
            gradient_canvas.place_forget()
        else:
            gradient_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        draw_gradient(root)

    for frame in [login_frame, register_frame]:
        frame.configure(bg=bg)
        for widget in frame.winfo_children():
            cls = widget.__class__.__name__
            try:
                if cls == 'RoundedButton':
                    widget.configure(bg=btn_bg, fg=fg, hover_bg=btn_hover_bg,
                                     font=font.Font(family=DEFAULT_FONT, size=BUTTON_FONT_SIZE))
                elif cls in ['Label']:
                    if widget.cget("text") in ("Login", "Register"):
                        widget.configure(bg=bg, fg=fg, font=font.Font(family=HEADING_FONT, size=HEADING_FONT_SIZE))
                    else:
                        widget.configure(bg=bg, fg=label_fg,
                                         font=font.Font(family=DEFAULT_FONT, size=LABEL_FONT_SIZE))  # Changed label color
                elif cls == 'RoundedEntry':
                    widget.configure(bg="#3A3A3A" if is_dark_mode else "#FFFFFF",
                                     fg=fg, insertbackground=fg,
                                     font=font.Font(family=DEFAULT_FONT, size=ENTRY_FONT_SIZE))
                elif cls == 'OptionMenu':
                    widget.configure(bg=btn_bg, fg=fg, highlightthickness=0,
                                     font=font.Font(family=DEFAULT_FONT, size=LABEL_FONT_SIZE))
                    widget["menu"].config(bg=btn_bg, fg=fg)
            except Exception as e:
                print(f"Theme error on {widget}: {e}")

    btn_theme.configure(bg=btn_bg, fg=fg,
                        font=font.Font(family=DEFAULT_FONT, size=BUTTON_FONT_SIZE))

# --- Custom Widgets ---
class RoundedEntry(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=parent['bg'])
        self.canvas = tk.Canvas(self, height=30, bd=0, highlightthickness=0,
                               relief='ridge', bg=parent['bg'])
        self.canvas.pack(fill='both', expand=True)
        self._show = ''
        entry_kwargs = {k: v for k, v in kwargs.items() if k not in ('show',)}
        self.entry = tk.Entry(self, bd=0, highlightthickness=0, show=self._show, **entry_kwargs)
        self.entry.place(x=8, y=4, width=250, height=22)
        self.draw_rounded_rect()
        self.configure(bg=parent['bg'])

    def draw_rounded_rect(self):
        radius = 12
        width = 270
        height = 30
        self.canvas.delete("all")
        self.canvas.create_arc((0, 0, radius * 2, radius * 2), start=90, extent=90,
                               fill=self['bg'], outline="")
        self.canvas.create_arc((width - radius * 2, 0, width, radius * 2), start=0,
                               extent=90, fill=self['bg'], outline="")
        self.canvas.create_arc((0, height - radius * 2, radius * 2, height), start=180,
                               extent=90, fill=self['bg'], outline="")
        self.canvas.create_arc((width - radius * 2, height - radius * 2, width, height),
                               start=270, extent=90, fill=self['bg'], outline="")
        self.canvas.create_rectangle(radius, 0, width - radius, height,
                                    fill=self['bg'], outline="")
        self.canvas.create_rectangle(0, radius, width, height - radius,
                                    fill=self['bg'], outline="")

    def get(self):
        return self.entry.get()

    def insert(self, index, string):
        self.entry.insert(index, string)

    def delete(self, first, last=None):
        self.entry.delete(first, last)

    def config(self, **kwargs):
        self.entry.config(**kwargs)

    def show(self):
        return self._show

    def toggle_show(self):
        if self._show == '*':
            self._show = ''
        else:
            self._show = '*'
        self.entry.config(show=self._show)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, **kwargs):
        super().__init__(parent, width=200, height=40, bd=0, highlightthickness=0,
                         relief='ridge')
        self.command = command
        self.text = text
        self.is_hover = False
        self.bg_color = kwargs.get('bg', '#E0E0E0')
        self.fg_color = kwargs.get('fg', '#000000')
        self.hover_bg = kwargs.get('hover_bg', '#C0C0C0')
        self.font = kwargs.get('font', font.Font(family=DEFAULT_FONT, size=BUTTON_FONT_SIZE))

        self.configure(bg=parent['bg'])
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.draw_button()

    def draw_button(self):
        self.delete("all")
        radius = 20
        width = int(self['width'])
        height = int(self['height'])
        bg = self.hover_bg if self.is_hover else self.bg_color

        self.create_oval(0, 0, radius * 2, height, fill=bg, outline=bg)
        self.create_oval(width - radius * 2, 0, width, height, fill=bg, outline=bg)
        self.create_rectangle(radius, 0, width - radius, height, fill=bg,
                                 outline=bg)
        self.create_text(width // 2, height // 2, text=self.text, fill=self.fg_color,
                         font=self.font)

    def on_click(self, event):
        if self.command:
            self.command()

    def on_enter(self, event):
        self.is_hover = True
        self.draw_button()

    def on_leave(self, event):
        self.is_hover = False
        self.draw_button()

# --- User Authentication Functions ---
def register_user():
    email = reg_entry.get()
    password = reg_entry_password.get()
    marital_status = var_marital.get()

    if not email or not password or not marital_status:
        messagebox.showerror("Error", "Please fill all fields")
        return

    if "@" not in email or "." not in email:
        messagebox.showerror("Error", "Invalid email format")
        return

    if len(password) < 8:
        messagebox.showerror("Error", "Password must be at least 8 characters")
        return

    hashed_pw = hash_password(password)
    conn = get_database_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL,
                            marital_status TEXT NOT NULL,  
                            role TEXT
                            )""")
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            messagebox.showerror("Error", "Email already registered")
        else:
            cursor.execute("INSERT INTO users (email, password, marital_status, role) VALUES (?, ?, ?, ?)",
                            (email, hashed_pw, marital_status, None)) #Added marital status to insert
            conn.commit()
            messagebox.showinfo("Success", "Registration successful! Please login.")
            switch_to_login()
    except Exception as e:
        messagebox.showerror("Database Error", str(e))
    finally:
        if conn:  # Ensure connection is closed
            conn.close()

def login_user():
    email = login_entry.get()
    password = login_entry_password.get()
    if not email or not password:
        messagebox.showerror("Error", "Please enter both email and password")
        return
    hashed_pw = hash_password(password)
    conn = get_database_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?",
                        (email, hashed_pw))
        user = cursor.fetchone()
        conn.close()
        if user:
            messagebox.showinfo("Success", "Login successful!")
            root.destroy()
            import main
            main.start_main_app(user)
        else:
            messagebox.showerror("Login Failed", "Invalid email or password")
    except Exception as e:
        messagebox.showerror("Database Error", str(e))
    finally:
        if conn: #ensure conn is closed
            conn.close()

# --- UI Control Helpers ---
def toggle_register_pw():
    reg_entry_password.toggle_show()

def toggle_login_pw():
    login_entry_password.toggle_show()

def switch_to_login():
    register_frame.pack_forget()
    login_frame.pack(fill='both', expand=True)

def switch_to_register():
    login_frame.pack_forget()
    register_frame.pack(fill='both', expand=True)

# --- Main Application ---
def main():
    global root, login_frame, register_frame, reg_entry, reg_entry_password, \
        var_marital, login_entry, login_entry_password, btn_theme

    root = tk.Tk()
    root.title("User Login & Register")
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = 420
    window_height = 420
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)

    load_theme_preference()

    # Initialize fonts
    custom_font = font.Font(family=DEFAULT_FONT, size=BUTTON_FONT_SIZE)  # Changed to BUTTON_FONT_SIZE
    heading_font = font.Font(family=HEADING_FONT, size=HEADING_FONT_SIZE)

    create_gradient_canvas(root)
    draw_gradient(root)
    animate_gradient(root)

    btn_theme = tk.Button(root, text="Toggle Theme",
                            command=lambda: toggle_theme(root))
    btn_theme.pack(pady=5)

    # --- Register Frame ---
    register_frame = tk.Frame(root, bg=root['bg'])
    tk.Label(register_frame, text="Register", font=heading_font, bg=root['bg'], fg="#000").pack(pady=10)

    tk.Label(register_frame, text="Email", bg=root['bg'], fg="#555").pack(pady=5)  # Label color
    reg_entry = RoundedEntry(register_frame, bg="#fff", fg="#000",
                                insertbackground="#000")
    reg_entry.pack(pady=2)

    tk.Label(register_frame, text="Password", bg=root['bg'], fg="#555").pack(pady=5)  # Label color
    reg_entry_password = RoundedEntry(register_frame, show="*", bg="#fff",
                                         fg="#000", insertbackground="#000")
    reg_entry_password.pack(pady=2)

    btn_show_pw_reg = RoundedButton(register_frame, text="Show/Hide Password",
                                     command=toggle_register_pw)
    btn_show_pw_reg.pack(pady=8)

    tk.Label(register_frame, text="Marital Status", bg=root['bg'], fg="#555").pack(pady=5)  # Label color
    var_marital = tk.StringVar(value="Single")
    marital_combobox = ttk.Combobox(register_frame, textvariable=var_marital, values=["Single", "Married"],
                                     font=font.Font(family=DEFAULT_FONT, size=ENTRY_FONT_SIZE),
                                     state="readonly")
    marital_combobox.pack(pady=2)

    btn_register = RoundedButton(register_frame, text="Register",
                                     command=register_user)
    btn_register.pack(pady=12)

    btn_switch_login = RoundedButton(register_frame,
                                         text="Already have an account? Login",
                                         command=switch_to_login)
    btn_switch_login.pack()

    # --- Login Frame ---
    login_frame = tk.Frame(root, bg=root['bg'])
    tk.Label(login_frame, text="Login", font=heading_font, bg=root['bg'], fg="#000").pack(pady=10)

    tk.Label(login_frame, text="Email", bg=root['bg'], fg="#555").pack(pady=5)  # Label color
    login_entry = RoundedEntry(login_frame, bg="#fff", fg="#000",
                                 insertbackground="#000")
    login_entry.pack(pady=2)

    tk.Label(login_frame, text="Password", bg=root['bg'], fg="#555").pack(pady=5)  # Label color
    login_entry_password = RoundedEntry(login_frame, show="*", bg="#fff",
                                          fg="#000", insertbackground="#000")
    login_entry_password.pack(pady=2)

    btn_show_pw_login = RoundedButton(login_frame, text="Show/Hide Password",
                                         command=toggle_login_pw)
    btn_show_pw_login.pack(pady=8)

    btn_login = RoundedButton(login_frame, text="Login", command=login_user)
    btn_login.pack(pady=12)

    btn_switch_register = RoundedButton(login_frame, text="New user? Register",
                                          command=switch_to_register)
    btn_switch_register.pack()

    # --- Initial Setup ---
    switch_to_login()
    apply_theme(root)
    root.bind("<Configure>", lambda event: draw_gradient(root))
    root.mainloop()

if __name__ == "__main__":
    main()
