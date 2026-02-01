import datetime
import sqlite3
from tkcalendar import DateEntry
from tkinter import *
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from tkinter import simpledialog
from tkinter import Toplevel
import json # For saving/loading report templates

# Attempt to import Matplotlib
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt # Though direct pyplot might not be used, good to have for colormaps etc.
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not found. Charts will not be available. Please install it: pip install matplotlib")


# Connecting to the Database
connector = sqlite3.connect("Expense Tracker.db")
cursor = connector.cursor()

# Updated table schema
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
# Budget Table
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS Budgets (
        ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        Category TEXT NOT NULL,
        Amount FLOAT NOT NULL,
        Period TEXT NOT NULL UNIQUE -- e.g., "YYYY-MM" for monthly budgets
    )'''
)
# New table for Saved Report Templates
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS ReportTemplates (
        ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        Name TEXT NOT NULL UNIQUE,
        SearchTerm TEXT,
        FilterDateRange TEXT,
        CustomStartDate TEXT,
        CustomEndDate TEXT,
        FilterMoP TEXT,
        FilterCategory TEXT
    )'''
)
# New table for Achievements
cursor.execute(
    '''CREATE TABLE IF NOT EXISTS Achievements (
        ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        Name TEXT NOT NULL UNIQUE,
        Description TEXT,
        AchievedDate DATETIME
    )'''
)
connector.commit()

# --- Global Variables for UI and Logic ---
# For sorting
current_sort_column = 'ID'
current_sort_direction = 'ASC'

# To store available categories
available_categories = ["All", "Food", "Travel", "Utilities", "Entertainment", "Education", "Shopping", "Health", "Salary", "Gifts", "Other"]
try:
    cursor.execute("SELECT DISTINCT Category FROM ExpenseTracker WHERE Category IS NOT NULL AND Category != ''")
    db_categories = [row[0] for row in cursor.fetchall()]
    for cat in db_categories:
        if cat not in available_categories:
            available_categories.append(cat)
    available_categories.sort(key=lambda x: (x == "All", x)) # Keep "All" first
except sqlite3.Error as e:
    print(f"Database error fetching categories: {e}")

available_mops = ["All", "Cash", "Cheque", "Credit Card", "Debit Card", "Online Transfer", "UPI", "Paytm", "Google Pay", "PhonePe", "Other"]

# --- Main Window and Tkinter Variables ---
root = Tk()
root.title('Enhanced Expense Tracker')
root.geometry('1450x800') # Increased window size for tabs
root.resizable(True, True)

# --- Initialize Tkinter Variables AFTER root window is created ---
desc = StringVar()
amnt = DoubleVar()
payee = StringVar()
MoP = StringVar(value='Cash')
category_var = StringVar(value='Food')
tags_var = StringVar()

search_query_var = StringVar()
filter_date_range_var = StringVar(value="All Time")
filter_mop_var = StringVar(value="All")
filter_category_var = StringVar(value="All")

# Changed currency symbol to ₹
total_expenses_var = StringVar(value="Total Expenses: N/A") # For summary display

# --- Theming Variables ---
current_theme_name = StringVar(value="Default")
themes = {
    "Default": {
        "primary_color": '#66b3ff',
        "secondary_color": '#ffcc80',
        "background_color": '#f0f4f8',
        "text_color": '#2c3e50',
        "button_text_color": '#ffffff',
        "hlb_btn_bg": '#66b3ff',
        "hlb_btn_bg_alt": '#ff8c00',
        "error_color": '#dc3545',
        "table_even_row": '#e9ecef',
        "table_odd_row": '#ffffff'
    },
    "Dark Mode": {
        "primary_color": '#34495e',
        "secondary_color": '#5d6d7e',
        "background_color": '#2c3e50',
        "text_color": '#ecf0f1',
        "button_text_color": '#ffffff',
        "hlb_btn_bg": '#3498db',
        "hlb_btn_bg_alt": '#e67e22',
        "error_color": '#e74c3c',
        "table_even_row": '#3b536b',
        "table_odd_row": '#4a647e'
    },
    "High Contrast": {
        "primary_color": '#000000',
        "secondary_color": '#ffffff',
        "background_color": '#000000',
        "text_color": '#ffffff',
        "button_text_color": '#000000',
        "hlb_btn_bg": '#ffffff',
        "hlb_btn_bg_alt": '#cccccc',
        "error_color": '#ff0000',
        "table_even_row": '#333333',
        "table_odd_row": '#000000'
    }
}

# Apply initial theme
current_theme = themes[current_theme_name.get()]
primary_color = current_theme["primary_color"]
secondary_color = current_theme["secondary_color"]
background_color = current_theme["background_color"]
text_color = current_theme["text_color"]
button_text_color = current_theme["button_text_color"]
hlb_btn_bg = current_theme["hlb_btn_bg"]
hlb_btn_bg_alt = current_theme["hlb_btn_bg_alt"]
error_color = current_theme["error_color"]

font_family = 'Open Sans'
heading_font_size = 16
body_font_size = 11
button_font_size = 12
label_font_size = 10

lbl_font = (font_family, label_font_size)
entry_font = (font_family, body_font_size, 'normal')
btn_font = (font_family, button_font_size, 'bold')

# --- Global UI Elements (that need to be accessed by multiple functions) ---
table = None
category_filter_dropdown = None
category_entry_dropdown = None
custom_start_date_label = None
custom_start_date = None
custom_end_date_label = None
custom_end_date = None
pie_chart_canvas_agg = None # For Matplotlib canvas
bar_chart_canvas_agg = None # For Matplotlib canvas
pie_ax = None
bar_ax = None
notebook = None # Reference to the main notebook widget

# --- Tooltip Class ---
class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = 0
        self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + self.widget.winfo_rooty() + 27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def create_tooltip(widget, text):
    toolTip = ToolTip(widget)
    def enter(event):
        toolTip.showtip(text)
    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)


# --- Functions ---

def apply_theme(theme_name):
    """Applies the selected theme colors to the UI elements."""
    global primary_color, secondary_color, background_color, text_color, \
           button_text_color, hlb_btn_bg, hlb_btn_bg_alt, error_color

    if theme_name not in themes:
        mb.showerror("Theme Error", f"Theme '{theme_name}' not found.")
        return

    current_theme = themes[theme_name]
    primary_color = current_theme["primary_color"]
    secondary_color = current_theme["secondary_color"]
    background_color = current_theme["background_color"]
    text_color = current_theme["text_color"]
    button_text_color = current_theme["button_text_color"]
    hlb_btn_bg = current_theme["hlb_btn_bg"]
    hlb_btn_bg_alt = current_theme["hlb_btn_bg_alt"]
    error_color = current_theme["error_color"]

    # Update root window and main header
    root.configure(bg=background_color)
    root.children['!label'].configure(bg=primary_color, fg=button_text_color) # Accessing the header label

    # Update notebook tabs (requires restyling ttk.Notebook)
    style.configure("TNotebook", background=background_color)
    style.configure("TNotebook.Tab", background=primary_color, foreground=button_text_color, font=(font_family, body_font_size, 'bold'))
    style.map("TNotebook.Tab", background=[("selected", secondary_color)], foreground=[("selected", text_color)])
    
    # Update frames
    for widget in root.winfo_children():
        if isinstance(widget, Frame) or isinstance(widget, ttk.Frame):
            widget.configure(bg=background_color)
        for child in widget.winfo_children():
            if isinstance(child, Frame) or isinstance(child, ttk.Frame):
                child.configure(bg=background_color)
            if isinstance(child, Label):
                child.configure(bg=background_color, fg=text_color)
            if isinstance(child, Button):
                child.configure(bg=hlb_btn_bg, fg=button_text_color)
            if isinstance(child, Entry):
                child.configure(bg=current_theme["table_odd_row"], fg=text_color) # Entry background
            if isinstance(child, ttk.Combobox):
                child.configure(background=current_theme["table_odd_row"], foreground=text_color)
            # Special handling for specific buttons that use different colors
            if child.cget("text") == 'Delete All Expenses':
                child.configure(bg=error_color)
            if child.cget("text") in ['Delete Selected', 'Clear Entry Fields', 'View/Load to Edit', 'Selected to Sentence', 'Reset', 'Manage Budgets']:
                 child.configure(bg=secondary_color, fg=text_color)

    # Update table styling
    style.configure("Custom.Treeview", background=current_theme["table_odd_row"], foreground=text_color,
                    fieldbackground=current_theme["table_odd_row"], font=(font_family, body_font_size-1))
    style.configure("Custom.Treeview.Heading", background=primary_color, foreground=button_text_color)
    table.tag_configure('evenrow', background=current_theme["table_even_row"])
    table.tag_configure('oddrow', background=current_theme["table_odd_row"])
    
    # Redraw charts to apply new background/colors if Matplotlib is available
    if MATPLOTLIB_AVAILABLE:
        pie_ax.set_facecolor(current_theme["table_odd_row"])
        bar_ax.set_facecolor(current_theme["table_odd_row"])
        pie_ax.tick_params(axis='x', colors=text_color)
        pie_ax.tick_params(axis='y', colors=text_color)
        bar_ax.tick_params(axis='x', colors=text_color)
        bar_ax.tick_params(axis='y', colors=text_color)
        bar_ax.xaxis.label.set_color(text_color)
        bar_ax.yaxis.label.set_color(text_color)
        pie_ax.title.set_color(text_color)
        bar_ax.title.set_color(text_color)
        if pie_chart_canvas_agg: pie_chart_canvas_agg.draw()
        if bar_chart_canvas_agg: bar_chart_canvas_agg.draw()


def get_all_categories_from_db():
    """Fetches all unique categories from the database and updates available_categories global list."""
    global available_categories
    try:
        cursor.execute("SELECT DISTINCT Category FROM ExpenseTracker WHERE Category IS NOT NULL AND Category != '' ORDER BY Category")
        db_categories = [row[0] for row in cursor.fetchall()]
        
        # Start with "All" and then unique categories
        # Use a temporary set to ensure "Other", "Food etc. from default list are also included if not in DB yet.
        current_defaults = set(["Food", "Travel", "Utilities", "Entertainment", "Education", "Shopping", "Health", "Salary", "Gifts", "Other"])
        for cat_db in db_categories:
            current_defaults.add(cat_db)

        updated_categories = ["All"] + sorted(list(current_defaults))
        available_categories = updated_categories
        
        # Update dropdowns if they exist and are valid Tkinter widgets
        if category_filter_dropdown and isinstance(category_filter_dropdown, ttk.Combobox):
            category_filter_dropdown['values'] = available_categories
        if category_entry_dropdown and isinstance(category_entry_dropdown, ttk.Combobox):
            category_entry_dropdown['values'] = [cat for cat in available_categories if cat != "All"]

    except sqlite3.Error as e:
        print(f"Database error fetching categories: {e}")
    except Exception as e: # Catch other potential Tkinter errors if widgets are not ready
        print(f"Error updating category dropdowns: {e}")
    return available_categories


def build_query_and_params(search_term=None, filters=None, sort_column='ID', sort_direction='ASC'):
    """Helper function to build the SQL query and parameters for fetching expenses.
       Supports enhanced search syntax (e.g., 'amount > 50', 'category:food')."""
    query = 'SELECT * FROM ExpenseTracker'
    conditions = []
    params = []

    # Enhanced Search
    if search_term:
        search_parts = search_term.split(' AND ') # Basic support for AND
        for part in search_parts:
            part = part.strip()
            if ':' in part: # Field-specific search (e.g., 'category:food', 'payee:starbucks')
                field, value = part.split(':', 1)
                field = field.strip().lower()
                value = value.strip().lower()
                
                if field in ['payee', 'description', 'category', 'tags', 'modeofpayment']:
                    conditions.append(f"LOWER({field}) LIKE ?")
                    params.append(f'%{value}%')
                elif field == 'amount': # Amount specific search (e.g., 'amount:>100', 'amount:<50', 'amount:=25')
                    if value.startswith('>='):
                        conditions.append("Amount >= ?")
                        params.append(float(value[2:]))
                    elif value.startswith('>'):
                        conditions.append("Amount > ?")
                        params.append(float(value[1:]))
                    elif value.startswith('<='):
                        conditions.append("Amount <= ?")
                        params.append(float(value[2:]))
                    elif value.startswith('<'):
                        conditions.append("Amount < ?")
                        params.append(float(value[1:]))
                    elif value.startswith('='):
                        conditions.append("Amount = ?")
                        params.append(float(value[1:]))
                    else: # Exact amount
                        conditions.append("Amount = ?")
                        params.append(float(value))
                elif field == 'date': # Date specific search (e.g., 'date:2023-01-15', 'date:>=2023-01-01')
                    if value.startswith('>='):
                        conditions.append("Date >= ?")
                        params.append(value[2:])
                    elif value.startswith('>'):
                        conditions.append("Date > ?")
                        params.append(value[1:])
                    elif value.startswith('<='):
                        conditions.append("Date <= ?")
                        params.append(value[2:])
                    elif value.startswith('<'):
                        conditions.append("Date < ?")
                        params.append(value[1:])
                    elif value.startswith('='):
                        conditions.append("Date = ?")
                        params.append(value[1:])
                    else: # Exact date
                        conditions.append("Date = ?")
                        params.append(value)
            else: # General search across multiple fields if no specific field is given
                search_conditions_list = []
                search_params_list = []
                general_search_fields = ['Payee', 'Description', 'Amount', 'Category', 'Tags', 'ModeOfPayment']
                for field in general_search_fields:
                    search_conditions_list.append(f"LOWER({field}) LIKE ?")
                    search_params_list.append(f'%{part.lower()}%')
                if search_conditions_list:
                    conditions.append("(" + " OR ".join(search_conditions_list) + ")")
                    params.extend(search_params_list)
            
    # Filters (existing logic)
    if filters:
        if filters.get('date_range') and filters['date_range'] != "All Time":
            start_date_val, end_date_val = None, None
            today = datetime.date.today()
            if filters['date_range'] == "Today":
                start_date_val = end_date_val = today
            elif filters['date_range'] == "This Week":
                start_date_val = today - datetime.timedelta(days=today.weekday())
                end_date_val = start_date_val + datetime.timedelta(days=6)
            elif filters['date_range'] == "This Month":
                start_date_val = today.replace(day=1)
                try:
                    end_date_val = (start_date_val + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
                except ValueError: # Handles months like December
                    end_date_val = start_date_val.replace(month=12, day=31)

            elif filters['date_range'] == "This Year":
                start_date_val = today.replace(month=1, day=1)
                end_date_val = today.replace(month=12, day=31)
            elif filters['date_range'] == "Custom Range" and filters.get('custom_start') and filters.get('custom_end'):
                try:
                    start_date_str = filters['custom_start']
                    end_date_str = filters['custom_end']
                    start_date_val = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date_val = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    mb.showerror("Invalid Date", "Custom date format is invalid. Please use YYYY-MM-DD.")
                    return None, None # Indicate error

            if start_date_val and end_date_val:
                conditions.append("Date BETWEEN ? AND ?")
                params.extend([start_date_val.strftime('%Y-%m-%d'), end_date_val.strftime('%Y-%m-%d 23:59:59')])

        if filters.get('mop') and filters['mop'] != "All":
            conditions.append("ModeOfPayment = ?")
            params.append(filters['mop'])
        if filters.get('category') and filters['category'] != "All":
            conditions.append("Category = ?")
            params.append(filters['category'])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    valid_sort_columns = ['ID', 'Date', 'Payee', 'Description', 'Amount', 'ModeOfPayment', 'Category', 'Tags']
    if sort_column not in valid_sort_columns: sort_column = 'ID'
    if sort_direction.upper() not in ['ASC', 'DESC']: sort_direction = 'ASC'
    query += f' ORDER BY "{sort_column}" {sort_direction.upper()}'
    
    return query, tuple(params)


def list_all_expenses(search_term=None, filters=None, sort_column='ID', sort_direction='ASC'):
    global connector, table
    if not table: return # Table not initialized yet

    table.delete(*table.get_children())
    
    query, params = build_query_and_params(search_term, filters, sort_column, sort_direction)
    if query is None: return # Error in building query (e.g. bad custom date)

    current_total_expenses = 0.0
    try:
        all_data = connector.execute(query, params)
        data_for_table = all_data.fetchall() # Fetch all for table display

        for i, values in enumerate(data_for_table):
            if len(values) == 8:
                display_date = values[1]
                if isinstance(display_date, str) and len(display_date) > 10: # Check if it's a full datetime string
                    try:
                        display_date = datetime.datetime.strptime(display_date.split(" ")[0], '%Y-%m-%d').strftime('%Y-%m-%d')
                    except ValueError: pass # Keep original if parsing fails
                
                amount_val = values[4]
                current_total_expenses += float(amount_val if amount_val else 0)

                # Changed currency symbol to ₹
                formatted_values = (values[0], display_date, values[2], values[3], f"₹{float(amount_val if amount_val else 0):.2f}", values[5], values[6], values[7])
                table.insert('', END, values=formatted_values, tags=('evenrow' if i % 2 == 0 else 'oddrow',))
            else:
                print(f"Warning: Row has unexpected columns: {values}")
        
        # Changed currency symbol to ₹
        total_expenses_var.set(f"Total Expenses (Filtered): ₹{current_total_expenses:.2f}")

    except sqlite3.Error as e:
        mb.showerror("Database Error", f"Fetching expenses failed: {e}\nQuery: {query}\nParams: {params}")
    
    get_all_categories_from_db()


def apply_search_and_filters():
    search_term = search_query_var.get()
    filters = {
        'date_range': filter_date_range_var.get(),
        'mop': filter_mop_var.get(),
        'category': filter_category_var.get()
    }
    if filters['date_range'] == "Custom Range":
        if custom_start_date and custom_end_date:
            try:
                filters['custom_start'] = custom_start_date.get_date().strftime('%Y-%m-%d')
                filters['custom_end'] = custom_end_date.get_date().strftime('%Y-%m-%d')
            except AttributeError:
                 mb.showerror("Custom Date Error", "Please select valid start and end dates.")
                 return
        else: # Should not happen if UI is built correctly
            mb.showerror("UI Error", "Custom date pickers not found.")
            return
    list_all_expenses(search_term=search_term, filters=filters, sort_column=current_sort_column, sort_direction=current_sort_direction)
    update_charts() # Auto-update charts on filter change


def reset_search_and_filters():
    search_query_var.set("")
    filter_date_range_var.set("All Time")
    filter_mop_var.set("All")
    filter_category_var.set("All")
    if custom_start_date: custom_start_date.set_date(datetime.date.today())
    if custom_end_date: custom_end_date.set_date(datetime.date.today())
    toggle_custom_date_fields()
    list_all_expenses(sort_column=current_sort_column, sort_direction=current_sort_direction)
    update_charts() # Auto-update charts


def sort_by_column_header(column_name):
    global current_sort_column, current_sort_direction
    if current_sort_column == column_name:
        current_sort_direction = 'DESC' if current_sort_direction == 'ASC' else 'ASC'
    else:
        current_sort_column = column_name
        current_sort_direction = 'ASC'
    
    for col_id in table['columns']: # Update header text
        text = table.heading(col_id, 'text').replace(' ▲', '').replace(' ▼', '')
        if col_id == column_name:
            text += ' ▲' if current_sort_direction == 'ASC' else ' ▼'
        table.heading(col_id, text=text)
    apply_search_and_filters()


def clear_entry_fields():
    desc.set('')
    payee.set('')
    amnt.set(0.0)
    MoP.set('Cash')
    category_var.set('Food')
    tags_var.set('')
    if date_entry: date_entry.set_date(datetime.datetime.now().date())
    if table: table.selection_remove(*table.selection())


def remove_expense_from_db():
    if not table or not table.selection():
        mb.showerror('No record selected!', 'Please select a record to delete.')
        return
    selected_item = table.item(table.focus())
    expense_id = selected_item['values'][0]
    payee_name = selected_item['values'][2]

    if mb.askyesno('Confirm Delete', f'Delete expense for {payee_name} (ID: {expense_id})?'):
        try:
            connector.execute('DELETE FROM ExpenseTracker WHERE ID=?', (expense_id,))
            connector.commit()
            apply_search_and_filters()
            mb.showinfo('Success', 'Expense deleted successfully.')
            check_and_award_achievements() # Check achievements after deletion
        except sqlite3.Error as e:
            mb.showerror("Database Error", f"Could not delete: {e}")


def remove_all_expenses_from_db():
    if mb.askyesno('Confirm Delete All', 'DELETE ALL expenses from the database? This cannot be undone.', icon='warning'):
        try:
            if table: table.delete(*table.get_children())
            connector.execute('DELETE FROM ExpenseTracker')
            connector.commit()
            clear_entry_fields()
            apply_search_and_filters()
            mb.showinfo('Success', 'All expenses deleted.')
            check_and_award_achievements() # Check achievements after deletion
        except sqlite3.Error as e:
            mb.showerror("Database Error", f"Could not delete all: {e}")


def add_expense_to_db():
    if not date_entry.get_date() or not payee.get() or not desc.get() or not amnt.get() or not MoP.get() or not category_var.get():
        mb.showerror('Fields Empty', "Fill all mandatory fields (Date, Payee, Description, Amount, MoP, Category).")
        return
    try:
        amount_val = float(amnt.get())
        if amount_val < 0:
            mb.showerror('Invalid Amount', 'Amount cannot be negative.')
            return
    except ValueError:
        mb.showerror('Invalid Amount', 'Enter a valid number for amount.')
        return
    
    current_cat = category_var.get()
    if current_cat and current_cat not in available_categories and current_cat != "All":
        available_categories.append(current_cat)
        get_all_categories_from_db() # This will sort and update dropdowns

    try:
        connector.execute(
            'INSERT INTO ExpenseTracker (Date, Payee, Description, Amount, ModeOfPayment, Category, Tags) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (date_entry.get_date().strftime('%Y-%m-%d'), payee.get(), desc.get(), amnt.get(), MoP.get(), current_cat, tags_var.get())
        )
        connector.commit()
        clear_entry_fields()
        apply_search_and_filters()
        mb.showinfo('Success', 'Expense added.')
        check_and_award_achievements() # Check achievements after adding
        display_personalized_recommendation() # Show recommendation after adding
    except sqlite3.Error as e:
        mb.showerror("Database Error", f"Could not add: {e}")


def open_edit_save_dialog(expense_id_to_edit=None):
    """Opens a modal dialog to add a new expense or edit an existing one."""
    dialog = Toplevel(root)
    dialog.transient(root) # Make it modal with respect to the root window
    dialog.grab_set() # Capture all events
    dialog.title("Edit Expense" if expense_id_to_edit else "Add New Expense")
    dialog.geometry("400x450")
    dialog.resizable(False, False)
    dialog.configure(bg=background_color)

    # Variables for the dialog's entry fields
    dlg_date_var = StringVar()
    dlg_payee_var = StringVar()
    dlg_desc_var = StringVar()
    dlg_amnt_var = DoubleVar()
    dlg_mop_var = StringVar()
    dlg_cat_var = StringVar()
    dlg_tags_var = StringVar()

    # Populate fields if editing
    if expense_id_to_edit:
        try:
            cursor.execute("SELECT Date, Payee, Description, Amount, ModeOfPayment, Category, Tags FROM ExpenseTracker WHERE ID = ?", (expense_id_to_edit,))
            data = cursor.fetchone()
            if data:
                # Format date correctly for DateEntry
                date_obj = datetime.datetime.strptime(data[0].split(" ")[0], '%Y-%m-%d').date()
                # dlg_date_var will be set by DateEntry directly
                dlg_payee_var.set(data[1])
                dlg_desc_var.set(data[2])
                dlg_amnt_var.set(data[3])
                dlg_mop_var.set(data[4])
                dlg_cat_var.set(data[5] if data[5] else "Other")
                dlg_tags_var.set(data[6] if data[6] else "")
            else:
                mb.showerror("Error", "Could not load expense data.", parent=dialog)
                dialog.destroy()
                return
        except Exception as e:
            mb.showerror("Error", f"Failed to load expense: {e}", parent=dialog)
            dialog.destroy()
            return
    else: # Defaults for adding new
        # date_obj will be today for new DateEntry
        dlg_mop_var.set("Cash")
        dlg_cat_var.set("Food")


    # Dialog UI Elements
    form_frame = Frame(dialog, bg=background_color, padx=20, pady=20)
    form_frame.pack(fill=BOTH, expand=True)

    Label(form_frame, text="Date:", font=lbl_font, bg=background_color).grid(row=0, column=0, sticky=W, pady=2)
    dlg_date_entry = DateEntry(form_frame, date_pattern='y-mm-dd', font=entry_font, width=35, selectmode='day', relief=SOLID, borderwidth=1)
    if expense_id_to_edit and data: dlg_date_entry.set_date(date_obj)
    else: dlg_date_entry.set_date(datetime.date.today())
    dlg_date_entry.grid(row=1, column=0, columnspan=2, sticky=W+E, pady=(0,10))
    
    Label(form_frame, text="Payee:", font=lbl_font, bg=background_color).grid(row=2, column=0, sticky=W, pady=2)
    Entry(form_frame, textvariable=dlg_payee_var, font=entry_font, width=37, relief=SOLID, borderwidth=1).grid(row=3, column=0, columnspan=2, sticky=W+E, pady=(0,10))

    Label(form_frame, text="Description:", font=lbl_font, bg=background_color).grid(row=4, column=0, sticky=W, pady=2)
    Entry(form_frame, textvariable=dlg_desc_var, font=entry_font, width=37, relief=SOLID, borderwidth=1).grid(row=5, column=0, columnspan=2, sticky=W+E, pady=(0,10))

    Label(form_frame, text="Amount:", font=lbl_font, bg=background_color).grid(row=6, column=0, sticky=W, pady=2)
    Entry(form_frame, textvariable=dlg_amnt_var, font=entry_font, width=37, relief=SOLID, borderwidth=1).grid(row=7, column=0, columnspan=2, sticky=W+E, pady=(0,10))
    
    Label(form_frame, text="Mode of Payment:", font=lbl_font, bg=background_color).grid(row=8, column=0, sticky=W, pady=2)
    dlg_mop_options = [m for m in available_mops if m != "All"]
    ttk.Combobox(form_frame, textvariable=dlg_mop_var, values=dlg_mop_options, font=entry_font, width=35, state="readonly").grid(row=9, column=0, columnspan=2, sticky=W+E, pady=(0,10))

    Label(form_frame, text="Category:", font=lbl_font, bg=background_color).grid(row=10, column=0, sticky=W, pady=2)
    dlg_cat_options = [c for c in available_categories if c != "All"]
    ttk.Combobox(form_frame, textvariable=dlg_cat_var, values=dlg_cat_options, font=entry_font, width=35).grid(row=11, column=0, columnspan=2, sticky=W+E, pady=(0,10))
    
    Label(form_frame, text="Tags (comma-separated):", font=lbl_font, bg=background_color).grid(row=12, column=0, sticky=W, pady=2)
    Entry(form_frame, textvariable=dlg_tags_var, font=entry_font, width=37, relief=SOLID, borderwidth=1).grid(row=13, column=0, columnspan=2, sticky=W+E, pady=(0,15))

    def on_save():
        # Validation
        if not dlg_date_entry.get_date() or not dlg_payee_var.get() or not dlg_desc_var.get() or not dlg_amnt_var.get() or not dlg_mop_var.get() or not dlg_cat_var.get():
            mb.showerror('Fields Empty', "Fill all mandatory fields.", parent=dialog)
            return
        try:
            amount_val = float(dlg_amnt_var.get())
            if amount_val < 0:
                mb.showerror('Invalid Amount', 'Amount cannot be negative.', parent=dialog)
                return
        except ValueError:
            mb.showerror('Invalid Amount', 'Enter a valid number for amount.', parent=dialog)
            return

        new_cat = dlg_cat_var.get()
        if new_cat and new_cat not in available_categories and new_cat != "All":
            available_categories.append(new_cat)
            get_all_categories_from_db() # Update global list and other dropdowns

        try:
            if expense_id_to_edit:
                connector.execute(
                    'UPDATE ExpenseTracker SET Date=?, Payee=?, Description=?, Amount=?, ModeOfPayment=?, Category=?, Tags=? WHERE ID=?',
                    (dlg_date_entry.get_date().strftime('%Y-%m-%d'), dlg_payee_var.get(), dlg_desc_var.get(), dlg_amnt_var.get(),
                     dlg_mop_var.get(), new_cat, dlg_tags_var.get(), expense_id_to_edit)
                )
            else: # This part is not currently used as "Add" uses the main panel. Kept for potential future use.
                pass # connector.execute('INSERT INTO ...')
            connector.commit()
            apply_search_and_filters() # Refresh main table
            mb.showinfo("Success", "Expense saved successfully.", parent=dialog)
            dialog.destroy()
            check_and_award_achievements() # Check achievements after editing
        except sqlite3.Error as e:
            mb.showerror("Database Error", f"Could not save: {e}", parent=dialog)

    button_frame = Frame(dialog, bg=background_color, pady=10)
    button_frame.pack(fill=X)
    
    save_btn = Button(button_frame, text="Save Changes", command=on_save, font=btn_font, bg=hlb_btn_bg, fg=button_text_color, width=15)
    save_btn.pack(side=LEFT, padx=(0,10), expand=True)
    cancel_btn = Button(button_frame, text="Cancel", command=dialog.destroy, font=btn_font, bg=secondary_color, fg=text_color, width=15)
    cancel_btn.pack(side=RIGHT, padx=(10,0), expand=True)
    
    dialog.wait_window() # Important for modal behavior


def trigger_edit_dialog():
    if not table or not table.selection():
        mb.showerror('No expense selected', 'Please select an expense from the table to edit.')
        return
    selected_item = table.item(table.focus())
    expense_id = selected_item['values'][0]
    open_edit_save_dialog(expense_id_to_edit=expense_id)


def selected_expense_to_words_action():
    if not table or not table.selection():
        mb.showerror('No expense selected!', 'Please select an expense from the table.')
        return
    values = table.item(table.focus())['values']
    # Changed currency symbol to ₹
    message = f'Paid ₹{values[4].replace("₹", "")} to {values[2]} for "{values[3]}" on {values[1]} via {values[5]}. Category: {values[6]}, Tags: {values[7]}.'
    mb.showinfo('Expense Details', message)


def expense_to_words_before_adding_action():
    if not date_entry.get_date() or not desc.get() or not amnt.get() or not payee.get() or not MoP.get() or not category_var.get():
        mb.showerror('Incomplete data', 'Fill all mandatory fields first!')
        return
    try:
        float(amnt.get())
    except ValueError:
        mb.showerror('Invalid Amount', 'Enter a valid number for amount.')
        return
    # Changed currency symbol to ₹
    message = f'Pay ₹{amnt.get()} to {payee.get()} for "{desc.get()}" on {date_entry.get_date().strftime("%Y-%m-%d")} via {MoP.get()}. Category: {category_var.get()}, Tags: {tags_var.get()}'
    if mb.askyesno('Confirm Expense', f'{message}\n\nAdd to database?'):
        add_expense_to_db()


def toggle_custom_date_fields(event=None):
    if not (custom_start_date_label and custom_start_date and custom_end_date_label and custom_end_date):
        return # Widgets not initialized
    if filter_date_range_var.get() == "Custom Range":
        custom_start_date_label.grid()
        custom_start_date.grid()
        custom_end_date_label.grid()
        custom_end_date.grid()
    else:
        custom_start_date_label.grid_remove()
        custom_start_date.grid_remove()
        custom_end_date_label.grid_remove()
        custom_end_date.grid_remove()

# --- Charting Functions ---
def update_charts():
    if not MATPLOTLIB_AVAILABLE:
        # mb.showwarning("Charting Disabled", "Matplotlib library is not installed. Charts cannot be displayed.")
        return

    # Fetch currently filtered data for charts
    search_term = search_query_var.get()
    filters = {
        'date_range': filter_date_range_var.get(),
        'mop': filter_mop_var.get(),
        'category': filter_category_var.get()
    }
    if filters['date_range'] == "Custom Range":
        if custom_start_date and custom_end_date:
            try:
                filters['custom_start'] = custom_start_date.get_date().strftime('%Y-%m-%d')
                filters['custom_end'] = custom_end_date.get_date().strftime('%Y-%m-%d')
            except AttributeError: return # Not ready
        else: return # Not ready
    
    query, params = build_query_and_params(search_term, filters)
    if query is None: return

    try:
        cursor.execute(query, params)
        all_filtered_data = cursor.fetchall()
    except sqlite3.Error as e:
        mb.showerror("Chart Data Error", f"Could not fetch data for charts: {e}")
        return

    plot_category_pie_chart(all_filtered_data)
    plot_monthly_bar_chart(all_filtered_data)


def plot_category_pie_chart(data):
    global pie_ax, pie_chart_canvas_agg
    if not MATPLOTLIB_AVAILABLE or not pie_ax or not pie_chart_canvas_agg: return

    pie_ax.clear() # Clear previous plot
    if not data:
        pie_ax.text(0.5, 0.5, "No data for pie chart.", ha='center', va='center', color=text_color)
        pie_chart_canvas_agg.draw()
        return

    category_spending = {}
    for row in data: # ID, Date, Payee, Description, Amount, ModeOfPayment, Category, Tags
        # Ensure row has enough columns before accessing index 6 and 4
        if len(row) > 6:  # Check if index 6 (Category) is accessible
            category = row[6] if row[6] else "Uncategorized"
        else:
            category = "Unknown Category" # Default or handle as appropriate for missing data
            # print(f"Warning: Row has insufficient columns for category: {row}") # Log unexpected row structure

        if len(row) > 4: # Check if index 4 (Amount) is accessible
            amount = float(row[4] if row[4] else 0)
        else:
            amount = 0.0 # Default or handle as appropriate for missing data
            # print(f"Warning: Row has insufficient columns for amount: {row}") # Log unexpected row structure
            continue # Skip this row if amount is critical and missing

        category_spending[category] = category_spending.get(category, 0) + amount
    
    if not category_spending:
        pie_ax.text(0.5, 0.5, "No category spending to display.", ha='center', va='center', color=text_color)
        pie_chart_canvas_agg.draw()
        return

    labels = category_spending.keys()
    sizes = category_spending.values()
    
    # Use a Matplotlib colormap for diverse colors
    colors = plt.cm.get_cmap('viridis', len(labels)) # 'viridis' is a good default

    pie_ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=[colors(i) for i in range(len(labels))])
    pie_ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    pie_ax.set_title("Spending by Category", fontsize=10, color=text_color)
    pie_chart_canvas_agg.draw()


def plot_monthly_bar_chart(data):
    global bar_ax, bar_chart_canvas_agg
    if not MATPLOTLIB_AVAILABLE or not bar_ax or not bar_chart_canvas_agg: return
    
    bar_ax.clear()
    if not data:
        bar_ax.text(0.5, 0.5, "No data for bar chart.", ha='center', va='center', color=text_color)
        bar_chart_canvas_agg.draw()
        return

    monthly_spending = {} # Key: "YYYY-MM", Value: total_amount
    for row in data:
        try:
            # Ensure row has enough columns before accessing index 1 and 4
            if len(row) > 1: # Check if index 1 (Date) is accessible
                date_obj = datetime.datetime.strptime(row[1].split(" ")[0], '%Y-%m-%d')
                month_year = date_obj.strftime("%Y-%m")
            else:
                # print(f"Warning: Row has insufficient columns for date: {row}")
                continue # Skip if date is missing

            if len(row) > 4: # Check if index 4 (Amount) is accessible
                amount = float(row[4] if row[4] else 0)
            else:
                amount = 0.0
                # print(f"Warning: Row has insufficient columns for amount: {row}")
                continue # Skip if amount is missing

            monthly_spending[month_year] = monthly_spending.get(month_year, 0) + amount
        except ValueError:
            # print(f"Warning: Could not parse date or amount for row: {row}")
            continue # Skip if date is malformed

    if not monthly_spending:
        bar_ax.text(0.5, 0.5, "No monthly spending to display.", ha='center', va='center', color=text_color)
        bar_chart_canvas_agg.draw()
        return
        
    sorted_months = sorted(monthly_spending.keys())
    amounts = [monthly_spending[month] for month in sorted_months]
    
    bar_ax.bar(sorted_months, amounts, color=primary_color)
    bar_ax.set_xlabel("Month (YYYY-MM)", fontsize=8, color=text_color)
    # Changed currency symbol to ₹
    bar_ax.set_ylabel("Total Spending (₹)", fontsize=8, color=text_color)
    bar_ax.set_title("Monthly Spending Trend", fontsize=10, color=text_color)
    bar_ax.tick_params(axis='x', rotation=45, labelsize=7, colors=text_color)
    bar_ax.tick_params(axis='y', labelsize=7, colors=text_color)
    bar_ax.grid(axis='y', linestyle='--', alpha=0.7, color=text_color)
    plt.tight_layout() # Adjust layout to prevent labels from overlapping (for the bar chart figure)
    bar_chart_canvas_agg.draw()

# --- Budgeting Functions (Basic) ---
def manage_budgets():
    category = simpledialog.askstring("Set Budget", "Enter Category (e.g., Food, Travel, or 'Overall'):", parent=root)
    if not category: return

    month_year = simpledialog.askstring("Set Budget", f"Enter Month for '{category}' budget (YYYY-MM):", parent=root)
    if not month_year: return
    try: # Validate YYYY-MM format
        datetime.datetime.strptime(month_year, "%Y-%m")
    except ValueError:
        mb.showerror("Invalid Format", "Month format must be YYYY-MM.", parent=root)
        return

    amount_str = simpledialog.askstring("Set Budget", f"Enter Budget Amount for '{category}' in {month_year} (₹):", parent=root)
    if not amount_str: return
    try:
        amount = float(amount_str)
        if amount < 0:
            mb.showerror("Invalid Amount", "Budget amount cannot be negative.", parent=root)
            return
    except ValueError:
        mb.showerror("Invalid Amount", "Please enter a valid number for the budget.", parent=root)
        return

    try:
        # Use INSERT OR REPLACE to update if exists, or insert if new for that period-category
        cursor.execute("INSERT OR REPLACE INTO Budgets (Category, Amount, Period) VALUES (?, ?, ?)",
                       (category.strip(), amount, month_year.strip()))
        connector.commit()
        # Changed currency symbol to ₹
        mb.showinfo("Budget Set", f"Budget for {category} in {month_year} set to ₹{amount:.2f}.", parent=root)
        update_progress_visualization() # Update progress after budget change
    except sqlite3.Error as e:
        mb.showerror("Database Error", f"Could not set budget: {e}", parent=root)


def get_budget_for_category(category, period_yyyy_mm):
    """Retrieves budget for a given category and period (YYYY-MM)."""
    try:
        cursor.execute("SELECT Amount FROM Budgets WHERE Category = ? AND Period = ?", (category, period_yyyy_mm))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Error fetching budget for {category} in {period_yyyy_mm}: {e}")
        return None

# --- Custom Reporting Templates ---
def save_current_report_template():
    template_name = simpledialog.askstring("Save Report Template", "Enter a name for this report template:", parent=root)
    if not template_name: return

    # Get current filter settings
    current_filters = {
        'SearchTerm': search_query_var.get(),
        'FilterDateRange': filter_date_range_var.get(),
        'CustomStartDate': custom_start_date.get_date().strftime('%Y-%m-%d') if custom_start_date and filter_date_range_var.get() == "Custom Range" else "",
        'CustomEndDate': custom_end_date.get_date().strftime('%Y-%m-%d') if custom_end_date and filter_date_range_var.get() == "Custom Range" else "",
        'FilterMoP': filter_mop_var.get(),
        'FilterCategory': filter_category_var.get()
    }

    try:
        cursor.execute("INSERT OR REPLACE INTO ReportTemplates (Name, SearchTerm, FilterDateRange, CustomStartDate, CustomEndDate, FilterMoP, FilterCategory) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (template_name, current_filters['SearchTerm'], current_filters['FilterDateRange'],
                        current_filters['CustomStartDate'], current_filters['CustomEndDate'],
                        current_filters['FilterMoP'], current_filters['FilterCategory']))
        connector.commit()
        mb.showinfo("Template Saved", f"Report template '{template_name}' saved successfully.")
    except sqlite3.Error as e:
        mb.showerror("Database Error", f"Could not save template: {e}")

def load_report_template():
    try:
        cursor.execute("SELECT Name FROM ReportTemplates ORDER BY Name")
        templates = [row[0] for row in cursor.fetchall()]
        if not templates:
            mb.showinfo("No Templates", "No saved report templates found.")
            return

        selected_template = simpledialog.askstring("Load Report Template", "Select a template to load:\n" + "\n".join(templates), parent=root)
        if not selected_template or selected_template not in templates:
            return

        cursor.execute("SELECT SearchTerm, FilterDateRange, CustomStartDate, CustomEndDate, FilterMoP, FilterCategory FROM ReportTemplates WHERE Name = ?", (selected_template,))
        template_data = cursor.fetchone()
        if template_data:
            search_query_var.set(template_data[0])
            filter_date_range_var.set(template_data[1])
            if template_data[1] == "Custom Range":
                if custom_start_date: custom_start_date.set_date(datetime.datetime.strptime(template_data[2], '%Y-%m-%d').date())
                if custom_end_date: custom_end_date.set_date(datetime.datetime.strptime(template_data[3], '%Y-%m-%d').date())
            toggle_custom_date_fields() # Ensure custom date fields are shown/hidden correctly
            filter_mop_var.set(template_data[4])
            filter_category_var.set(template_data[5])
            apply_search_and_filters()
            mb.showinfo("Template Loaded", f"Report template '{selected_template}' loaded.")
        else:
            mb.showerror("Error", "Could not load selected template.")
    except sqlite3.Error as e:
        mb.showerror("Database Error", f"Error loading template: {e}")
    except ValueError as e:
        mb.showerror("Date Error", f"Error parsing date in template: {e}")

# --- Personalized Recommendations ---
def get_spending_summary():
    """Calculates total spending per category for the last 30 days."""
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    query = "SELECT Category, SUM(Amount) FROM ExpenseTracker WHERE Date BETWEEN ? AND ? GROUP BY Category"
    try:
        cursor.execute(query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d 23:59:59')))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching spending summary for recommendations: {e}")
        return []

def display_personalized_recommendation():
    """Analyzes spending and provides a simple recommendation."""
    spending_summary = get_spending_summary()
    total_spending = sum(amount for _, amount in spending_summary)

    recommendation_text = "No specific recommendations yet. Keep tracking your expenses!"

    if total_spending > 0:
        # Find the category with the highest spending
        most_spent_category = None
        max_spending = 0
        for category, amount in spending_summary:
            if amount > max_spending:
                max_spending = amount
                most_spent_category = category
        
        if most_spent_category:
            # Simple rule-based recommendation
            if most_spent_category.lower() in ["food", "entertainment", "shopping"] and max_spending / total_spending > 0.3:
                recommendation_text = f"You spend a significant amount on '{most_spent_category}'. Consider setting a budget for this category or looking for alternatives to save money!"
            elif total_spending > 1000 and len(spending_summary) > 5:
                recommendation_text = "You're tracking many categories! Review your spending trends in the 'Reports & Summary' tab to find areas for savings."
            else:
                recommendation_text = "Great job tracking your expenses! Keep an eye on your spending in different categories."
    
    # Display recommendation in a small, non-intrusive way, e.g., a temporary label or a dedicated section.
    # For now, let's use a messagebox for simplicity. In a real app, this would be a small pop-up or a dashboard widget.
    # mb.showinfo("Personalized Tip", recommendation_text)
    # Or update a label on the reports tab:
    if hasattr(root, 'recommendation_label'): # Check if label exists
        root.recommendation_label.config(text=f"Tip: {recommendation_text}")
    else:
        print(f"Tip: {recommendation_text}") # Fallback to print if UI element not ready

# --- Gamification: Achievements ---
achievements_list = [
    {"name": "First Step", "description": "Add your first expense.", "condition": lambda: get_expense_count() >= 1},
    {"name": "Budget Setter", "description": "Set your first budget.", "condition": lambda: get_budget_count() >= 1},
    {"name": "Fifty Expenses", "description": "Log 50 expenses.", "condition": lambda: get_expense_count() >= 50},
    {"name": "Monthly Tracker", "description": "Log expenses for 30 consecutive days (at least one per day).", "condition": lambda: check_consecutive_days_logged(30)},
    {"name": "Zero Debt Day", "description": "Have zero expenses for a day (requires no expenses logged today).", "condition": lambda: check_zero_expense_today()}
]

def get_expense_count():
    cursor.execute("SELECT COUNT(*) FROM ExpenseTracker")
    return cursor.fetchone()[0]

def get_budget_count():
    cursor.execute("SELECT COUNT(*) FROM Budgets")
    return cursor.fetchone()[0]

def check_consecutive_days_logged(days):
    # This is a simplified check. A more robust one would need to check for actual daily entries.
    # For now, just check if total expenses are high enough to imply consistent usage.
    # This needs actual date logic for proper implementation.
    # For demonstration, let's just use total expenses as a proxy.
    return get_expense_count() >= days * 2 # Assuming at least 2 expenses per day for 'days' days

def check_zero_expense_today():
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM ExpenseTracker WHERE Date = ?", (today_str,))
    return cursor.fetchone()[0] == 0

def check_and_award_achievements():
    """Checks conditions for all achievements and awards them if not already achieved."""
    for achievement in achievements_list:
        name = achievement["name"]
        description = achievement["description"]
        condition_func = achievement["condition"]

        cursor.execute("SELECT AchievedDate FROM Achievements WHERE Name = ?", (name,))
        if cursor.fetchone() is None: # Not yet achieved
            if condition_func():
                try:
                    achieved_date = datetime.date.today().strftime('%Y-%m-%d')
                    cursor.execute("INSERT INTO Achievements (Name, Description, AchievedDate) VALUES (?, ?, ?)",
                                   (name, description, achieved_date))
                    connector.commit()
                    mb.showinfo("Achievement Unlocked!", f"Congratulations! You unlocked: {name}\n\n{description}")
                    update_achievements_display() # Refresh achievements tab
                except sqlite3.Error as e:
                    print(f"Error awarding achievement {name}: {e}")

def get_achievements():
    """Fetches all achieved achievements from the database."""
    cursor.execute("SELECT Name, Description, AchievedDate FROM Achievements ORDER BY AchievedDate DESC")
    return cursor.fetchall()

def update_achievements_display():
    """Refreshes the display on the Achievements tab."""
    if 'achievements_tree' in globals() and achievements_tree:
        achievements_tree.delete(*achievements_tree.get_children())
        achieved_data = get_achievements()
        for i, (name, desc, date) in enumerate(achieved_data):
            achievements_tree.insert('', END, values=(name, desc, date), tags=('evenrow' if i % 2 == 0 else 'oddrow',))

# --- Gamification: Savings Challenges & Progress Visualization ---
# This is a simplified example. A full implementation would need a dedicated challenge setup UI.
savings_goal_amount = 500.0 # This can remain a number, only display string changes
# Changed currency symbol to ₹
savings_goal_var = StringVar(value=f"Savings Goal: ₹0.00 / ₹{savings_goal_amount:.2f}")

def update_progress_visualization():
    global savings_goal_current
    # For simplicity, let's define "savings" as total income minus total expenses
    # assuming income is tracked, or just total expenses for a "reduce spending" goal.
    # Here, let's make it a "reduce spending by X" challenge.
    # Or, if we had an income field, we could calculate actual savings.

    # Let's assume a "No-Spend Week" challenge for simplicity:
    # Calculate spending for the last 7 days. If it's below a certain threshold, consider it "successful".
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=7)
    
    cursor.execute("SELECT SUM(Amount) FROM ExpenseTracker WHERE Date BETWEEN ? AND ?",
                   (seven_days_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d 23:59:59')))
    last_week_spending = cursor.fetchone()[0] or 0.0

    challenge_threshold = 100.0 # Example: Spend less than ₹100 last week
    
    if last_week_spending <= challenge_threshold:
        # Changed currency symbol to ₹
        savings_goal_var.set(f"No-Spend Week Challenge: SUCCESS! (Spent ₹{last_week_spending:.2f})")
        # You could also award an achievement here
    else:
        # Changed currency symbol to ₹
        savings_goal_var.set(f"No-Spend Week Challenge: Current: ₹{last_week_spending:.2f} (Target: <₹{challenge_threshold:.2f})")
    
    # Update a progress bar if available
    if 'savings_progress_bar' in globals() and savings_progress_bar:
        # Map spending to progress bar (inverse logic: lower spending = higher progress)
        max_val = 200 # Max spending for progress bar scale
        progress_val = max(0, min(max_val - last_week_spending, max_val)) # Invert for savings
        savings_progress_bar['value'] = (progress_val / max_val) * 100 # Convert to percentage

# --- UI Setup ---
root.configure(bg=background_color)
header_label = Label(root, text='EXPENSE TRACKER', font=(font_family, heading_font_size + 2, 'bold'), bg=primary_color, fg=button_text_color,
      padx=10, pady=10)
header_label.pack(side=TOP, fill=X)
create_tooltip(header_label, "Your personal financial tracker.")

# Notebook for Tabs
notebook = ttk.Notebook(root)
notebook.pack(pady=10, padx=10, fill=BOTH, expand=True)

# Tab 1: View & Manage Expenses
manage_tab = Frame(notebook, bg=background_color)
notebook.add(manage_tab, text=' View & Manage Expenses ')

data_entry_frame = Frame(manage_tab, bg=background_color, padx=15, pady=15)
data_entry_frame.place(x=0, y=0, width=320, relheight=1.0)

right_content_frame = Frame(manage_tab, bg=background_color, padx=10, pady=0)
right_content_frame.place(x=320, y=0, relwidth=0.75, relheight=1.0) # Adjusted relwidth

# Data Entry (Left Panel on Manage Tab)
Label(data_entry_frame, text='Date (YYYY-MM-DD):', font=lbl_font, bg=background_color).grid(row=0, column=0, sticky=W, pady=(0,2))
date_entry = DateEntry(data_entry_frame, date_pattern='y-mm-dd', font=entry_font, width=28, relief=SOLID, borderwidth=1)
date_entry.grid(row=1, column=0, sticky=W+E, pady=(0,8))
create_tooltip(date_entry, "Select the date of the expense.")

Label(data_entry_frame, text='Payee:', font=lbl_font, bg=background_color).grid(row=2, column=0, sticky=W, pady=(0,2))
payee_entry = Entry(data_entry_frame, font=entry_font, width=30, textvariable=payee, relief=SOLID, borderwidth=1)
payee_entry.grid(row=3, column=0, sticky=W+E, pady=(0,8))
create_tooltip(payee_entry, "Who did you pay?")

Label(data_entry_frame, text='Description:', font=lbl_font, bg=background_color).grid(row=4, column=0, sticky=W, pady=(0,2))
desc_entry = Entry(data_entry_frame, font=entry_font, width=30, textvariable=desc, relief=SOLID, borderwidth=1)
desc_entry.grid(row=5, column=0, sticky=W+E, pady=(0,8))
create_tooltip(desc_entry, "Brief description of the expense.")

Label(data_entry_frame, text='Amount:', font=lbl_font, bg=background_color).grid(row=6, column=0, sticky=W, pady=(0,2))
amnt_entry = Entry(data_entry_frame, font=entry_font, width=30, textvariable=amnt, relief=SOLID, borderwidth=1)
amnt_entry.grid(row=7, column=0, sticky=W+E, pady=(0,8))
create_tooltip(amnt_entry, "The amount of the expense.")

Label(data_entry_frame, text='Mode of Payment:', font=lbl_font, bg=background_color).grid(row=8, column=0, sticky=W, pady=(0,2))
mop_options_entry = [m for m in available_mops if m != "All"]
mop_dropdown_entry = ttk.Combobox(data_entry_frame, textvariable=MoP, values=mop_options_entry, font=entry_font, width=28, state='readonly')
MoP.set('Cash')
mop_dropdown_entry.grid(row=9, column=0, sticky=W+E, pady=(0,8))
create_tooltip(mop_dropdown_entry, "How did you pay for this?")

Label(data_entry_frame, text='Category:', font=lbl_font, bg=background_color).grid(row=10, column=0, sticky=W, pady=(0,2))
category_entry_options_list = [cat for cat in available_categories if cat != "All"]
category_entry_dropdown = ttk.Combobox(data_entry_frame, textvariable=category_var, values=category_entry_options_list, font=entry_font, width=28)
category_var.set('Food')
category_entry_dropdown.grid(row=11, column=0, sticky=W+E, pady=(0,8))
create_tooltip(category_entry_dropdown, "Categorize your expense.")

Label(data_entry_frame, text='Tags (comma-separated):', font=lbl_font, bg=background_color).grid(row=12, column=0, sticky=W, pady=(0,2))
tags_entry = Entry(data_entry_frame, font=entry_font, width=30, textvariable=tags_var, relief=SOLID, borderwidth=1)
tags_entry.grid(row=13, column=0, sticky=W+E, pady=(0,12))
create_tooltip(tags_entry, "Add keywords (e.g., 'travel', 'vacation').")

add_btn = Button(data_entry_frame, text='Add Expense', command=add_expense_to_db, font=btn_font, width=28, bg=hlb_btn_bg, fg=button_text_color, relief=RAISED, bd=2)
add_btn.grid(row=14, column=0, sticky=W+E, pady=4)
create_tooltip(add_btn, "Add the current expense to the database.")

convert_add_btn = Button(data_entry_frame, text='Convert to Words & Add', command=expense_to_words_before_adding_action, font=btn_font, width=28, bg=hlb_btn_bg, fg=button_text_color, relief=RAISED, bd=2)
convert_add_btn.grid(row=15, column=0, sticky=W+E, pady=4)
create_tooltip(convert_add_btn, "Review expense details as text before adding.")

# Search and Filter (Right Panel on Manage Tab, Top)
search_filter_controls_frame = Frame(right_content_frame, bg=background_color, pady=5)
search_filter_controls_frame.pack(side=TOP, fill=X)

sf_inner = Frame(search_filter_controls_frame, bg=background_color)
sf_inner.pack() # Center the controls

Label(sf_inner, text="Search:", font=lbl_font, bg=background_color).grid(row=0, column=0, padx=3, pady=3, sticky=E)
search_box = Entry(sf_inner, textvariable=search_query_var, font=entry_font, width=25, relief=SOLID, borderwidth=1)
search_box.grid(row=0, column=1, padx=3, pady=3, sticky=W)
search_box.bind("<Return>", lambda e: apply_search_and_filters())
create_tooltip(search_box, "Search by keyword or use 'field:value' (e.g., 'amount:>100', 'category:food').")

Label(sf_inner, text="Date:", font=lbl_font, bg=background_color).grid(row=1, column=0, padx=3, pady=3, sticky=E)
date_opts = ["All Time", "Today", "This Week", "This Month", "This Year", "Custom Range"]
date_filter_dd = ttk.Combobox(sf_inner, textvariable=filter_date_range_var, values=date_opts, font=entry_font, width=12, state='readonly')
date_filter_dd.grid(row=1, column=1, padx=3, pady=3, sticky=W)
date_filter_dd.bind("<<ComboboxSelected>>", toggle_custom_date_fields)
create_tooltip(date_filter_dd, "Filter expenses by date range.")

custom_start_date_label = Label(sf_inner, text="From:", font=lbl_font, bg=background_color)
custom_start_date = DateEntry(sf_inner, date_pattern='y-mm-dd', font=entry_font, width=10, relief=SOLID, borderwidth=1)
custom_end_date_label = Label(sf_inner, text="To:", font=lbl_font, bg=background_color)
custom_end_date = DateEntry(sf_inner, date_pattern='y-mm-dd', font=entry_font, width=10, relief=SOLID, borderwidth=1)
custom_start_date_label.grid(row=1, column=2, padx=(5,0), pady=3, sticky=E)
custom_start_date.grid(row=1, column=3, padx=3, pady=3, sticky=W)
custom_end_date_label.grid(row=1, column=4, padx=(5,0), pady=3, sticky=E)
custom_end_date.grid(row=1, column=5, padx=3, pady=3, sticky=W)
toggle_custom_date_fields() # Initial hide/show

Label(sf_inner, text="MoP:", font=lbl_font, bg=background_color).grid(row=0, column=2, padx=(10,0), pady=3, sticky=E)
mop_filter_dd = ttk.Combobox(sf_inner, textvariable=filter_mop_var, values=available_mops, font=entry_font, width=12, state='readonly')
mop_filter_dd.grid(row=0, column=3, padx=3, pady=3, sticky=W)
create_tooltip(mop_filter_dd, "Filter by Mode of Payment.")

Label(sf_inner, text="Category:", font=lbl_font, bg=background_color).grid(row=0, column=4, padx=(10,0), pady=3, sticky=E)
category_filter_dropdown = ttk.Combobox(sf_inner, textvariable=filter_category_var, values=available_categories, font=entry_font, width=12, state='readonly')
category_filter_dropdown.grid(row=0, column=5, padx=3, pady=3, sticky=W)
create_tooltip(category_filter_dropdown, "Filter by expense category.")

apply_btn_sf = Button(sf_inner, text="Apply", command=apply_search_and_filters, font=btn_font, bg=hlb_btn_bg, fg=button_text_color, relief=RAISED, bd=1, padx=5)
apply_btn_sf.grid(row=0, column=6, rowspan=1, padx=5, pady=3, sticky=W+E)
create_tooltip(apply_btn_sf, "Apply the selected search and filter criteria.")

reset_btn_sf = Button(sf_inner, text="Reset", command=reset_search_and_filters, font=btn_font, bg=secondary_color, fg=text_color, relief=RAISED, bd=1, padx=5)
reset_btn_sf.grid(row=1, column=6, rowspan=1, padx=5, pady=3, sticky=W+E)
create_tooltip(reset_btn_sf, "Clear all search and filter settings.")

# Report Template Buttons
template_buttons_frame = Frame(search_filter_controls_frame, bg=background_color, pady=5)
template_buttons_frame.pack(side=BOTTOM, fill=X)
Button(template_buttons_frame, text="Save Template", command=save_current_report_template, font=btn_font, bg=hlb_btn_bg, fg=button_text_color, relief=RAISED, bd=1, padx=5).pack(side=LEFT, padx=3)
Button(template_buttons_frame, text="Load Template", command=load_report_template, font=btn_font, bg=hlb_btn_bg, fg=button_text_color, relief=RAISED, bd=1, padx=3).pack(side=LEFT, padx=3)


# Action Buttons (Right Panel on Manage Tab, Middle)
action_buttons_frame = Frame(right_content_frame, bg=background_color, pady=5)
action_buttons_frame.pack(side=TOP, fill=X)
btn_params = {'font': btn_font, 'fg': button_text_color, 'relief': RAISED, 'bd': 2, 'width': 16, 'pady': 3}
delete_selected_btn = Button(action_buttons_frame, text='Delete Selected', bg=secondary_color, command=remove_expense_from_db, **btn_params)
delete_selected_btn.pack(side=LEFT, padx=3)
create_tooltip(delete_selected_btn, "Delete the currently selected expense.")

clear_entry_btn = Button(action_buttons_frame, text='Clear Entry Fields', bg=secondary_color, command=clear_entry_fields, **btn_params)
clear_entry_btn.pack(side=LEFT, padx=3)
create_tooltip(clear_entry_btn, "Clear all input fields on the left panel.")

delete_all_btn = Button(action_buttons_frame, text='Delete All Expenses', bg=error_color, command=remove_all_expenses_from_db, **btn_params)
delete_all_btn.pack(side=LEFT, padx=3)
create_tooltip(delete_all_btn, "Permanently delete ALL expenses. Use with caution!")

edit_btn = Button(action_buttons_frame, text='View/Load to Edit', bg=secondary_color, command=trigger_edit_dialog, **btn_params)
edit_btn.pack(side=LEFT, padx=3)
create_tooltip(edit_btn, "Open a dialog to view or edit the selected expense.")

to_sentence_btn = Button(action_buttons_frame, text='Selected to Sentence', bg=secondary_color, command=selected_expense_to_words_action, **btn_params)
to_sentence_btn.pack(side=LEFT, padx=3)
create_tooltip(to_sentence_btn, "Show details of the selected expense in a readable sentence.")


# Treeview (Right Panel on Manage Tab, Bottom)
tree_display_frame = Frame(right_content_frame, relief='groove', borderwidth=1)
tree_display_frame.pack(side=TOP, fill=BOTH, expand=True, pady=(5,0))
style = ttk.Style() # Ensure style is defined before use
style.configure("Custom.Treeview", highlightthickness=0, bd=0, font=(font_family, body_font_size-1))
style.configure("Custom.Treeview.Heading", font=(font_family, label_font_size, 'bold'), background=primary_color, foreground=button_text_color)
style.map("Custom.Treeview.Heading", relief=[('active','groove'),('pressed','sunken')])

cols = ('ID', 'Date', 'Payee', 'Description', 'Amount', 'ModeOfPayment', 'Category', 'Tags')
table = ttk.Treeview(tree_display_frame, columns=cols, show='headings', style="Custom.Treeview", selectmode=BROWSE)
table.tag_configure('evenrow', background=themes[current_theme_name.get()]["table_even_row"])
table.tag_configure('oddrow', background=themes[current_theme_name.get()]["table_odd_row"])

col_names = {'ID':'SNo', 'Date':'Date', 'Payee':'Payee', 'Description':'Description', 'Amount':'Amount', 'ModeOfPayment':'MoP', 'Category':'Category', 'Tags':'Tags'}
col_widths = {'ID':40, 'Date':85, 'Payee':120, 'Description':200, 'Amount':70, 'ModeOfPayment':100, 'Category':100, 'Tags':100}
for c in cols:
    table.heading(c, text=col_names[c], anchor=CENTER, command=lambda _c=c: sort_by_column_header(_c))
    table.column(c, width=col_widths[c], stretch=NO, anchor=CENTER if c not in ['Description', 'Payee'] else W)

ys = Scrollbar(tree_display_frame, orient=VERTICAL, command=table.yview)
xs = Scrollbar(tree_display_frame, orient=HORIZONTAL, command=table.xview)
table.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
ys.pack(side=RIGHT, fill=Y)
xs.pack(side=BOTTOM, fill=X)
table.pack(side=LEFT, fill=BOTH, expand=True)

# --- Keyboard Navigation Bindings (for main window) ---
root.bind('<Control-s>', lambda e: add_expense_to_db()) # Ctrl+S to Add Expense
root.bind('<Control-d>', lambda e: remove_expense_from_db()) # Ctrl+D to Delete Selected
root.bind('<Control-e>', lambda e: trigger_edit_dialog()) # Ctrl+E to Edit Selected
root.bind('<Control-r>', lambda e: reset_search_and_filters()) # Ctrl+R to Reset Filters
root.bind('<F5>', lambda e: apply_search_and_filters()) # F5 to Apply Filters


# Tab 2: Reports & Summary
reports_tab = Frame(notebook, bg=background_color, padx=20, pady=20)
notebook.add(reports_tab, text=' Reports & Summary ')

summary_frame = Frame(reports_tab, bg=background_color)
summary_frame.pack(side=TOP, fill=X, pady=(0,10))
Label(summary_frame, textvariable=total_expenses_var, font=(font_family, body_font_size, 'bold'), bg=background_color, fg=text_color).pack(side=LEFT)

# Personalized Recommendation Label
root.recommendation_label = Label(summary_frame, text="Tip: Analyzing your spending...", font=(font_family, body_font_size, 'italic'), bg=background_color, fg=text_color, wraplength=400, justify=LEFT)
root.recommendation_label.pack(side=RIGHT, padx=10)


charts_actions_frame = Frame(reports_tab, bg=background_color)
charts_actions_frame.pack(side=TOP, fill=X, pady=5)
Button(charts_actions_frame, text="Update Charts", command=update_charts, font=btn_font, bg=hlb_btn_bg, fg=button_text_color).pack(side=LEFT, padx=5)
Button(charts_actions_frame, text="Manage Budgets", command=manage_budgets, font=btn_font, bg=secondary_color, fg=text_color).pack(side=LEFT, padx=5)

# Progress Visualization (Example: No-Spend Week Challenge)
savings_progress_frame = Frame(reports_tab, bg=background_color, pady=10)
savings_progress_frame.pack(side=TOP, fill=X)
Label(savings_progress_frame, textvariable=savings_goal_var, font=lbl_font, bg=background_color, fg=text_color).pack(side=LEFT, padx=5)
savings_progress_bar = ttk.Progressbar(savings_progress_frame, orient="horizontal", length=200, mode="determinate")
savings_progress_bar.pack(side=LEFT, padx=5)


charts_display_frame = Frame(reports_tab, bg=background_color)
charts_display_frame.pack(side=TOP, fill=BOTH, expand=True, pady=10)

if MATPLOTLIB_AVAILABLE:
    # Pie Chart Frame (Left)
    pie_chart_frame = Frame(charts_display_frame, bg='white', relief=SUNKEN, borderwidth=1)
    pie_chart_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
    pie_fig = Figure(figsize=(5, 4), dpi=100) # width, height
    pie_ax = pie_fig.add_subplot(111)
    pie_chart_canvas_agg = FigureCanvasTkAgg(pie_fig, master=pie_chart_frame)
    pie_chart_canvas_agg.draw()
    pie_chart_canvas_agg.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

    # Bar Chart Frame (Right)
    bar_chart_frame = Frame(charts_display_frame, bg='white', relief=SUNKEN, borderwidth=1)
    bar_chart_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=5)
    bar_fig = Figure(figsize=(5, 4), dpi=100)
    bar_ax = bar_fig.add_subplot(111)
    bar_chart_canvas_agg = FigureCanvasTkAgg(bar_fig, master=bar_chart_frame)
    bar_chart_canvas_agg.draw()
    bar_chart_canvas_agg.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
else:
    Label(charts_display_frame, text="Matplotlib not installed. Charts are unavailable.", font=lbl_font, bg=background_color, fg=error_color).pack(pady=20)


# Tab 3: Achievements
achievements_tab = Frame(notebook, bg=background_color, padx=20, pady=20)
notebook.add(achievements_tab, text=' Achievements ')

achievements_tree_frame = Frame(achievements_tab, relief='groove', borderwidth=1)
achievements_tree_frame.pack(side=TOP, fill=BOTH, expand=True, pady=(5,0))

achievements_cols = ('Name', 'Description', 'Achieved Date')
achievements_tree = ttk.Treeview(achievements_tree_frame, columns=achievements_cols, show='headings', style="Custom.Treeview", selectmode=NONE)
achievements_tree.tag_configure('evenrow', background=themes[current_theme_name.get()]["table_even_row"])
achievements_tree.tag_configure('oddrow', background=themes[current_theme_name.get()]["table_odd_row"])

for c in achievements_cols:
    achievements_tree.heading(c, text=c, anchor=CENTER)
    achievements_tree.column(c, width=250, stretch=YES, anchor=CENTER)

achievements_ys = Scrollbar(achievements_tree_frame, orient=VERTICAL, command=achievements_tree.yview)
achievements_tree.configure(yscrollcommand=achievements_ys.set)
achievements_ys.pack(side=RIGHT, fill=Y)
achievements_tree.pack(side=LEFT, fill=BOTH, expand=True)


# Tab 4: Settings
settings_tab = Frame(notebook, bg=background_color, padx=20, pady=20)
notebook.add(settings_tab, text=' Settings ')

Label(settings_tab, text="Select Theme:", font=lbl_font, bg=background_color, fg=text_color).pack(pady=10)
theme_options = list(themes.keys())
theme_dropdown = ttk.Combobox(settings_tab, textvariable=current_theme_name, values=theme_options, font=entry_font, state='readonly')
theme_dropdown.set("Default") # Set initial value
theme_dropdown.pack(pady=5)
theme_dropdown.bind("<<ComboboxSelected>>", lambda e: apply_theme(current_theme_name.get()))


# --- Initial Load ---
get_all_categories_from_db() # Populate categories first
# Then update dropdowns that depend on these lists
if category_entry_dropdown: category_entry_dropdown['values'] = [cat for cat in available_categories if cat != "All"]
if category_filter_dropdown: category_filter_dropdown['values'] = available_categories
if mop_filter_dd: mop_filter_dd['values'] = available_mops
if mop_dropdown_entry: mop_dropdown_entry['values'] = [m for m in available_mops if m != "All"]

list_all_expenses(sort_column=current_sort_column, sort_direction=current_sort_direction)
sort_by_column_header(current_sort_column) # To set initial sort indicator
update_charts() # Initial chart draw
check_and_award_achievements() # Check achievements on startup
update_achievements_display() # Display achievements
update_progress_visualization() # Initial update for progress bar
display_personalized_recommendation() # Initial recommendation

root.mainloop()

connector.close()
