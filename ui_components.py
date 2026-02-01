import tkinter as tk

class LabeledEntry(tk.Frame):
    def __init__(self, parent, label_text, entry_width=20):
        super().__init__(parent)
        self.label = tk.Label(self, text=label_text)
        self.entry = tk.Entry(self, width=entry_width)
        self.label.pack(side=tk.LEFT, padx=5)
        self.entry.pack(side=tk.LEFT)

    def get(self):
        return self.entry.get()

    def set(self, text):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)
