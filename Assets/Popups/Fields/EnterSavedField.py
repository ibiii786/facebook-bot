import tkinter as tk
def make_enter_saved_field_popup(root, save_callback):
    popup = tk.Toplevel(root)
    popup.title("Save Fields")
    popup.geometry("300x150")

    
    label = tk.Label(popup, text="Enter Title for the fields, if the field is already saved it will be replaced:")
    label.pack(pady=10)
    
    entry = tk.Entry(popup)
    entry.pack(pady=5)
    
    def on_save():
        value = entry.get()
        save_callback(value)
        popup.destroy()
    
    save_button = tk.Button(popup, text="Save", command=on_save)
    save_button.pack(pady=10)
