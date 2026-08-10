
from tkinter import filedialog, messagebox
import tkinter as tk
from Assets.Constants.const import bg_color
def add_image_box(self, parent,px=5,max_images=11):
    if parent not in self.img_arr:
        self.img_arr[parent]=[]
    if len(self.img_arr[parent])>=10:
        messagebox.showwarning("Image Limit Reached", "You can't add more than 10 images.")
        return
    total_images=len(self.img_arr[parent])
    img_row = tk.Frame(parent, bg="#252526")
    col = total_images % max_images
    row = total_images // max_images
    img_row.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
    img_entry = tk.Entry(img_row, width=55, bg=bg_color, fg="white", insertbackground="white")
    remove_img_btn = tk.Button(
        img_row,
        text="❌",
        bg="#a83232",
        fg="white",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        command=lambda r=img_row: remove_image_box(self, r, img_entry, parent,max_images)
    )
    remove_img_btn.pack(side="top", padx=px,anchor='w')
    self.img_arr[parent].append(img_entry)
    self.add_img_btn[parent].grid_forget()
    self.add_img_btn[parent].grid(row=(len(self.img_arr[parent])//max_images), column=(len(self.img_arr[parent])%max_images), padx=5, pady=5, sticky="nsew")
    return img_entry, img_row
def browse_image(self, entry,img_row,thumbnail_size=(70,70),pass_self=True,max_images=11):
    file_paths = filedialog.askopenfilenames(
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")]
    )
    if file_paths:
        img_frame = img_row.master
        last_entry = self.img_arr[img_frame][-1]
        current = last_entry.get().strip()
        if current=="":
            entry.delete(0, "end")
            entry.insert(0,file_paths[0])
            addImg(self, img_row, file_paths[0],thumbnail_size,pass_self)
        else:
            img_entry, img_row2 = add_image_box(self,img_row.master,max_images=max_images)
            if  img_entry:
                img_entry.insert(0, file_paths[0])
                addImg(self, img_row2, file_paths[0],thumbnail_size,pass_self)
        
        for file_path in file_paths[1:]:
            img_entry, img_row2 = add_image_box(self,img_row.master,max_images=max_images)
            if not img_entry:
                break
            img_entry.insert(0, file_path)
            addImg(self, img_row2, file_path,thumbnail_size,pass_self)
def addImg(self,img_row,file_path,thumbnail_size=(70,70),pass_self=True):
    from PIL import Image, ImageTk
    from Assets.Popups.Images.ShowImg import show_full_image
    ImgBox=tk.Frame(img_row, bg="#2d2d30", bd=2, relief="groove",width=100, height=100)
    ImgBox.pack(fill="x", pady=2, padx=3)
    img = Image.open(file_path)
    img.thumbnail(thumbnail_size)
    tk_img = ImageTk.PhotoImage(img)
    img_label = tk.Label(ImgBox, image=tk_img, bg="#2d2d30",height=thumbnail_size[1], width=thumbnail_size[0])
    img_label.image = tk_img  # prevent garbage collection
    img_label.pack(pady=5)
    if not pass_self:
        self=img_label
    img_label.bind("<Button-1>", lambda e: show_full_image(self, file_path))
def remove_image_box(self, img_row, img_entry, parent,max_images):
    if len(self.img_arr[parent]) <= 1:
        messagebox.showwarning("Minimum Image Required", "At least one image is required.")
        return
    
    img_row.destroy()
    self.img_arr[parent].remove(img_entry)
    img_entry.destroy()

    # Re-grid all remaining image boxes with correct row/column positions
    for idx, img_box in enumerate(self.img_arr[parent]):
        row = idx // max_images
        col = idx % max_images
        img_box.master.grid_forget()
        img_box.master.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
  
    # Update add button position
    self.add_img_btn[parent].grid_forget()
    row = len(self.img_arr[parent]) // max_images
    col = len(self.img_arr[parent]) % max_images
    self.add_img_btn[parent].grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

import os
import random
from PIL import Image, ImageEnhance

def anti_fingerprint_image(image_path: str) -> str:
    """Strips EXIF data and subtly shifts image metadata/pixels to prevent duplicate hash detection by FB."""
    if not image_path or not os.path.exists(image_path):
        return image_path
    try:
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp_images"))
        os.makedirs(temp_dir, exist_ok=True)

        base_name = os.path.basename(image_path)
        name, ext = os.path.splitext(base_name)
        if not ext:
            ext = ".jpg"
        out_path = os.path.abspath(os.path.join(temp_dir, f"{name}_mod_{random.randint(1000, 9999)}{ext}"))

        with Image.open(image_path) as img:
            # Convert RGBA/P to RGB if JPG
            if img.mode in ("RGBA", "P") and ext.lower() in (".jpg", ".jpeg"):
                img = img.convert("RGB")

            # Slightly crop 1px to change MD5 and spatial hash
            w, h = img.size
            if w > 10 and h > 10:
                img = img.crop((1, 1, w - 1, h - 1))

            # Subtle brightness variation (0.99 to 1.01)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(random.uniform(0.99, 1.01))

            # Save clean image without EXIF metadata
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)
            clean_img.save(out_path, quality=95)
            return out_path
    except Exception as e:
        print(f"Anti-fingerprint image processing failed for {image_path}: {e}")
        return image_path