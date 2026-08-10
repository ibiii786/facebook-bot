import os
import tkinter as tk
from Assets.Constants.const import bg_color, main_color
from Assets.Files.DeleteFiles.DeleteFiles import delete_file
def load_states():
    if os.path.exists('./saved_states'):
        files = os.listdir('./saved_states')
        print(files)
        return files
    else:
        return []
def file_selected(root,callback, filename):
    root.destroy()
    pure_filename = os.path.join('./saved_states', filename)
    callback(pure_filename)
def file_deleted(root,filename,callback,file_root):
    delete_file(filename)
    root.destroy()
    load_states_popup(file_root,callback)
def load_states_popup(root,callback):
    files = load_states()
    popup = tk.Toplevel(root)
    top_label = tk.Label(
        popup, 
        text="Select Which data to load", 
        bg=bg_color, 
        fg="white", 
        font=("Segoe UI", 12, "bold")
    )
    top_label.pack(pady=(20, 10))
    popup.title("Loaded Files")
    popup.geometry("800x600")
    popup.configure(bg=bg_color)
    y_axis=0
    x_axis=0
    button_frame = tk.Frame(popup, bg=bg_color)
    button_frame.pack(expand=True, fill="both", padx=20, pady=20)
    for file in files:
        file_selection_frame = tk.Frame(button_frame, bg=main_color, relief="raised", bd=2)
        file_selection_frame.grid(row=y_axis, column=x_axis, padx=10, pady=10)
        file_label = tk.Label(file_selection_frame, text=file[:-4], bg=main_color, fg="white", font=("Segoe UI", 10))
        file_label.pack(pady=(0, 5))
        file_button_frame = tk.Frame(file_selection_frame, bg=main_color)
        load_button = tk.Button(file_button_frame, text="Load", width=10, bg="#0078D7", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", command=lambda f=file: file_selected(popup,callback,f))
        load_button.pack(side="left", padx=5)
        delete_button = tk.Button(file_button_frame, text="Delete", width=10, bg="#D9534F", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", command=lambda f=file: file_deleted(popup,f,callback,root))
        delete_button.pack(side="left", padx=5)
        file_button_frame.pack(padx=10, pady=10)
        x_axis+=1
        if x_axis==3:
            x_axis=0
            y_axis+=1
    popup.transient(root)  
    popup.grab_set()       
    popup.focus_force() 