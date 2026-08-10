import tkinter as tk
from tkinter import filedialog, messagebox
def handle_drop_video( event, entry,is_text_box=False):
    file = event.data.strip()
    file = file.replace("{", "").replace("}", "")  # TkDND sometimes wraps paths in {}
    if file.lower().endswith((".mp4", ".avi", ".mov", ".wmv")):
        if is_text_box:
            current_content = entry.get("1.0", "end").strip()
            if current_content:
                entry.insert("end", "\n" + file)
            else:
                entry.delete("1.0", "end")
                entry.insert("1.0", file)
        else:
            entry.delete(0, "end")
            entry.insert(0, file)
    else:
        tk.messagebox.showerror("Invalid File", "Please drop a valid video file.")
def browse_video(entry,is_text_box=False):
    file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv *.webm")])
    if file_path:
        if is_text_box:
            current_content = entry.get("1.0", "end").strip()
            if current_content:
                entry.insert("end", "\n" + file_path)
            else:
                entry.delete("1.0", "end")
                entry.insert("1.0", file_path)
        else:
            entry.delete(0, "end")
            entry.insert(0, file_path)