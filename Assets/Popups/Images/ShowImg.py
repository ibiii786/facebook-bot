from PIL import Image, ImageTk
import tkinter as tk
def show_full_image(self, file_path):
    preview = tk.Toplevel(self)
    preview.title("Image Preview")
    preview.configure(bg="#1e1e1e")
    preview.grab_set()  # modal window (optional)
    img = Image.open(file_path)
    screen_w = preview.winfo_screenwidth() - 200
    screen_h = preview.winfo_screenheight() - 200
    img.thumbnail((screen_w, screen_h))
    tk_img = ImageTk.PhotoImage(img)
    lbl = tk.Label(preview, image=tk_img, bg="#1e1e1e")
    lbl.image = tk_img
    lbl.pack(padx=20, pady=20)
    lbl.bind("<Button-1>", lambda e: preview.destroy())