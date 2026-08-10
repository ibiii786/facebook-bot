import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import multiprocessing
from Assets.Utils.Video.Video_controls import handle_drop_video,browse_video
from Open_fb import main,distribute_among_accounts
from renew import main as renew_main
from save_state_screen import main as save_state_main
from Assets.Popups.Fields.EnterSavedField import make_enter_saved_field_popup
import pandas as pd
from Assets.Files.SaveFiles.SaveFile import add_to_prev
from Assets.Popups.Fields.Loaded_Files import load_states_popup
from Assets.Popups.Save_Fields.Save_Field_Quickly import save_field_quickly_interface
from Assets.Constants.const import bg_color,main_color
from Assets.Utils.Scroll import on_key,on_scroll
from Assets.Utils.ImageHandling.Handle_image import add_image_box,browse_image,addImg
CSV_NAME="last_saved_state.csv"
class SceneApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.add_img_btn={}
        self.img_arr={}
        self.title("Facebook Marketplace Bulk Listing Bot")
        self.geometry("1200x750")
        self.configure(bg=bg_color)
        self.entries = []
        # --- Number of Processes ---
        proc_frame = tk.Frame(self, bg=bg_color)
        proc_frame.pack(pady=10)

        tk.Label(
            proc_frame,
            text="Total listings to renew",
            font=("Segoe UI", 11, "bold"),
            fg="white",
            bg=bg_color
        ).pack(side="left", padx=5)

        self.num_processes_var = tk.IntVar(value=2)
        proc_spinbox = tk.Spinbox(
            proc_frame,
            from_=1,
            to=100,
            textvariable=self.num_processes_var,
            width=5,
            font=("Segoe UI", 10),
            bg=bg_color,
            fg="white",
            justify="center",
            relief="flat",
            validate="key",
            validatecommand=(self.register(self.validate_int), "%P"),
            bd=2
        )
        proc_spinbox.pack(side="left", padx=5)

        # Renew Listings button to the right of the spinbox
        self.renew_btn = self.create_button(proc_frame, "🔁 Renew Listings", "#2e8b57",
                           lambda: self.renew_listings(),15)
        self.renew_btn.pack(side="left", padx=10)
        delete_and_relist_frame = tk.Frame(self, bg=bg_color)
        # Avoid expanding this frame which can cause its children to be clipped;
        # keep it full-width with some horizontal padding so buttons aren't cut off.
        delete_and_relist_frame.pack( padx=10,anchor="center")
        delete_and_relist_label = tk.Label(
            delete_and_relist_frame,
            text="Delete & Relist",
            font=("Segoe UI", 11, "bold"),
            fg="#cccccc",
            bg=bg_color
        )
        delete_and_relist_label.pack(side="left", padx=5)
        self.num_delete_relist_var = tk.IntVar(value=2)
        delete_and_relist_spinbox = tk.Spinbox(
            delete_and_relist_frame,
            from_=1,
            to=100,
            textvariable=self.num_delete_relist_var,
            width=5,
            font=("Segoe UI", 10, "bold"),
            bg=bg_color,
            fg="white",
            justify="center",
            relief="flat",
            validate="key",
            validatecommand=(self.register(self.validate_int), "%P"),
            bd=2
        )
        delete_and_relist_spinbox.pack(side="left", padx=5)
        self.delete_and_relist_btn = self.create_button(delete_and_relist_frame, "Delete & Relist", "#a83232",lambda: self.delete_and_relist_worker(),15)
        self.delete_and_relist_btn.pack(side="left", padx=10)
       

        # --- Button bar ---
        self.button_bar = tk.Frame(self, bg=bg_color)
        self.button_bar.pack(pady=10)
        #add field button
        self.add_button = self.create_button(self.button_bar, "➕ Add Field", "#2e8b57", self.add_field,11)
        self.add_button.pack(side="left", padx=10)
        #save field quickly button
        self.save_field_quickly_btn = self.create_button(self.button_bar, "💾 Save Field Quickly", "#0078d7", lambda: save_field_quickly_interface(self),16)
        self.save_field_quickly_btn.pack(side="left", padx=10)

        # self.save_button = self.create_button(self.button_bar, "💾 Save All", "#0078d7", self.save_all)
        # self.save_button.pack(side="left", padx=10)
        self.run_button = self.create_button(self.button_bar, "🤖 Run Bot", "#a83232", self.run_bot,10)
        self.run_button.pack(side="left", padx=10)
        # --- Status Label ---
        # Ensure long label wraps instead of being cut off
        self.distribute_btn = tk.Button(
            self.button_bar,
            text="📤 Distribute Among Accounts",
            bg="#0078d7",
            fg="white",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            wraplength=180,        # allow multi-line text so it's not clipped
            justify="center",
            padx=8,
            pady=4,
            command=lambda: self.run_distribute_bot()
        )
        #Run failed button
        self.run_failed_button = tk.Button(
            self.button_bar,
            text="Regenerate Failed Listings",
            bg="#bebe19",
            fg="white",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            wraplength=180,        # allow multi-line text so it's not clipped
            justify="center",
            padx=8,
            pady=4,
            command=lambda: self.run_failed_bot()
        )
        self.run_failed_button.pack(side="left", padx=10)
        #Save fields button
        self.save_fields_button = tk.Button(
            self.button_bar,
            text="💾 Save All Fields",
            bg="#0078d7",
            fg="white",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            wraplength=180,        # allow multi-line text so it's not clipped
            justify="center",
            padx=8,
            pady=4,
            command=lambda: self.save_fields()
        )
        self.save_fields_button.pack(side="left", padx=10)
        #Load saved fields button
        self.load_fields_button = tk.Button(
            self.button_bar,
            text="📂 Load Saved Fields",
            bg="#0078d7",
            fg="white",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            wraplength=180,        # allow multi-line text so it's not clipped
            justify="center",
            padx=8,
            pady=4,
            command=lambda: self.load_saved_fields()
        )
        self.load_fields_button.pack(side="left", padx=10)
        # waiting button styling to
        waiting_frame = tk.Frame(self, bg=bg_color)
        waiting_frame.pack( padx=5)
        tk.Label(
            waiting_frame,
            text="(Time between listings)",
            font=("Segoe UI", 11, "bold"),
            fg="white",
            bg=bg_color
        ).pack(side="left", padx=5)
        self.waiting_var = tk.IntVar(value=2)
        waiting_spinbox = tk.Spinbox(
            waiting_frame,
            from_=0,
            to=60,
            textvariable=self.waiting_var,
            width=5,
            font=("Segoe UI", 10),
            bg=bg_color,
            fg="white",
            justify="center",
            relief="flat",
            validate="key",
            validatecommand=(self.register(self.validate_int), "%P"),
            bd=2
        )
        waiting_spinbox.pack(side="left", padx=5)
        self.hours_minute_sec_dropdown = tk.StringVar(value="seconds")
        self.hours_minute_sec_menu = tk.OptionMenu(
            waiting_frame,
            self.hours_minute_sec_dropdown,
            "seconds",
            "minutes",
            "hours"
        )
        self.hours_minute_sec_menu.config(
            bg=bg_color,
            fg="white",
            relief="flat",
            font=("Segoe UI", 10),
            width=8
        )
        self.hours_minute_sec_menu.pack(side="left", padx=5)
        # keep hover behavior consistent with other buttons
        self.distribute_btn.bind("<Enter>", lambda e, b=self.distribute_btn, c="#0078d7": b.config(bg=self.shade_color(c, -20)))
        self.distribute_btn.bind("<Leave>", lambda e, b=self.distribute_btn, c="#0078d7": b.config(bg=c))
        self.distribute_btn.pack(side="left", padx=10)
        self.status_label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 11, "bold"),
            fg="#00ffff",
            bg=bg_color
        )
        self.status_label.pack(pady=2)
        # market input box
        market_grid = tk.Frame(self, bg=bg_color)
        # pack without fill so the frame sizes to its children and center it
        market_grid.pack(pady=2, anchor="center")

        market_label = tk.Label(
            market_grid,
            text="Select your marketplace location",
            font=("Segoe UI", 10, "italic"),
            fg="#cccccc",
            bg=bg_color
        )
        market_label.pack(side="left", padx=(10, 8), pady=2)

        self.country_var = tk.StringVar(value="UK")
        Uk_checkbox = tk.OptionMenu(market_grid, self.country_var, "UK", "Canada")
        Uk_checkbox.config(
            bg=bg_color,
            fg="white",
            relief="flat",
            font=("Segoe UI", 10),
            width=20
        )
        Uk_checkbox.pack(side="left", pady=2)

        # --- Scrollable Area ---
        container = tk.Frame(self, bg=bg_color)
        container.pack(fill="both", expand=True, pady=2)

        self.canvas = tk.Canvas(container, bg=bg_color, highlightthickness=0)
        self.canvas.focus_set()
        self.canvas.bind("<Key>", lambda e: on_key(e,self.canvas))
        self.bind_all("<MouseWheel>", lambda e: on_scroll(e, self.canvas))
        self.scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        self.scroll_frame = tk.Frame(self.canvas, bg=bg_color)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.scroll_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.scroll_window, width=e.width))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        # self.scrollbar.pack(side="right", fill="y")
        self.main_colour=main_color
        self.auto_grid_row = 0
        self.auto_grid_col = 0
    def load_saved_fields(self):
        import ast
        def callback(filename):
                df=pd.read_csv(filename)
                for col in ["Images", "Tags"]:
                    df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else [])
                    if 'Video' not in df.columns:
                        df['Video'] = ''
                    else:
                        df['Video'] = df['Video'].fillna('')
                print(len(self.entries))
                for _ in range(len(df)):
                    self.add_field()
                print(len(self.entries))
                idx=len(df)-1
                for entry in reversed(self.entries):
                    img_entries, title_entry, description_entry,category_entry, location_entry, tags_entry, price_entry, condition_entry, availability_entry, video_entry ,wrapper,opt_vars= entry
                    first=True
                    if idx<0:
                        break
                    for image in df.iloc[idx]["Images"]:
                        if first:
                            img_entries[0].delete(0, "end") 
                            first=False
                            img_entries[0].insert(0, image)
                            addImg(self,img_entries[0].master,image)
                        else:
                            img_entry,_= add_image_box(self,wrapper.winfo_children()[2].winfo_children()[1])
                            img_entry.delete(0, "end")
                            img_entry.insert(0, image)
                            addImg(self,img_entry.master,image)

                    title_entry.delete(0, "end")
                    title_entry.insert(0,df.iloc[idx]["Title"])
                    description_entry.delete("1.0", "end")
                    description_entry.insert("1.0",df.iloc[idx]["Description"])
                    category_entry.delete(0, "end")
                    category_entry.insert(0,df.iloc[idx]["Category"])
                    location_entry.delete(0, "end")
                    location_entry.insert(0,df.iloc[idx]["Location"])
                    tags_entry.delete(0, "end")
                    tags_entry.insert(0,",".join(df.iloc[idx]["Tags"]))
                    price_entry.delete(0, "end")
                    value = df.iloc[idx]["Price"]
                    print(f"Warning: Could not convert price '{value}' to a number. Leaving it as is.")
                    try:
                        if pd.isna(value):
                            raise ValueError("NaN value")
                        int_val = float(value)
                        price_entry.insert(0, int(int_val) if int_val.is_integer() else int_val)
                    except Exception as e:
                        print("Error thrown",e)
                        price_entry.insert(0, 0)
                    condition_entry.delete(0, "end")
                    condition_entry.insert(0,df.iloc[idx]["Condition"])
                    availability_entry.delete(0, "end")
                    availability_entry.insert(0,df.iloc[idx]["Availability"])

                    video_entry.delete(0, "end")
                    video_entry.insert(0,df.iloc[idx]["Video"])
                    public_meetup = df.iloc[idx]["Public meetup"] if not pd.isna(df.iloc[idx]["Public meetup"]) else 0
                    Door_pickup = df.iloc[idx]["Door pickup"] if not pd.isna(df.iloc[idx]["Door pickup"]) else 0
                    Door_dropoff = df.iloc[idx]["Door dropoff"] if not pd.isna(df.iloc[idx]["Door dropoff"]) else 0
                    opt_vars[0].set(public_meetup )
                    opt_vars[1].set(Door_pickup )
                    opt_vars[2].set(Door_dropoff )
                    idx-=1
        load_states_popup(self,callback)

    def save_fields(self):  
        df=pd.DataFrame(columns=["Images","Title","Videos","Description","Category","Location","Tags","Price","Condition","Availability","Video","Public meetup","Door pickup","Door dropoff"])
        for entry in self.entries:
            img_entries, title_entry, description_entry,category_entry, location_entry, tags_entry, price_entry, condition_entry, availability_entry, video_entry ,wrapper,opt_vars= entry
            if os.path.exists(CSV_NAME):
                os.remove(CSV_NAME)
            images_list = [img.get() for img in img_entries if img.get().strip()]
            print(images_list)
            df = df._append({
                "Images": images_list if len(images_list)>0 else None,
                "Title": title_entry.get(),
                "Description": description_entry.get("1.0", "end").strip(),
                "Category": category_entry.get(),
                "Location": location_entry.get(),
                "Tags": tags_entry.get().split(","),
                "Price": price_entry.get(),
                "Condition": condition_entry.get(),
                "Availability": availability_entry.get(),
                "Video": video_entry.get(),
                "Public meetup": opt_vars[0].get(),
                "Door pickup": opt_vars[1].get(),
                "Door dropoff": opt_vars[2].get()
            },ignore_index=True)
        def callback(value):
            add_to_prev(df,value)
        make_enter_saved_field_popup(self, callback)

    def run_failed_bot(self):
        save_state_main()
    def delete_and_relist_worker(self):
        self.disable_controls()
        self.status_label.config(text="🤖 Deleting and relisting listings... Please wait.")
        delete_thread = threading.Thread(target=self._delete_thread,daemon=True)
        delete_thread.start()
    def _delete_thread(self):
        try:
            relisting = self.num_delete_relist_var.get() or 2 
            renew_main(relisting,call="relist")
            self.after(0,self.enable_controls)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to delete and relist listings:\n{e}"))
            self.after(0, self.enable_controls)

    def renew_listings(self):
        self.disable_controls()
        self.status_label.config(text="🤖 Renewing listings... Please wait.")
        renew_thread = threading.Thread(target=self._renew_thread,daemon=True)
        renew_thread.start()
    def _renew_thread(self):
        try:
            process = self.num_processes_var.get() or 2 
            renew_main(process)
            self.after(0,self.enable_controls)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to renew listings:\n{e}"))
            self.after(0, self.enable_controls)

    # --- Button Styling ---
    def create_button(self, parent, text, color, command,Width=12):
        btn = tk.Button(
    parent,
    text=text,
    bg=color,
    fg="white",
    relief="flat",
    font=("Segoe UI", 11, "bold"),
    width=Width,
    command=command,
    wraplength=180,      # lower = wraps sooner
    justify="center",   # center-align wrapped lines
)
        btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg=self.shade_color(c, -20)))
        btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))
        return btn

    def validate_int(self, value):
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False

    def shade_color(self, color, percent):
        color = color.lstrip("#")
        r, g, b = int(color[:2], 16), int(color[2:4], 16), int(color[4:], 16)
        r = max(0, min(255, r + percent))
        g = max(0, min(255, g + percent))
        b = max(0, min(255, b + percent))
        return f"#{r:02x}{g:02x}{b:02x}"

    def field_design(self,parent,placeholder_text=""):
      # If auto-grid counters do not exist, create them
        if not hasattr(parent, "_grid_row"):
            parent._grid_row = 0
            parent._grid_col = 0

        # Place field at current row/col
        row = parent._grid_row
        col = parent._grid_col

        field_wrapper = tk.Frame(parent, bg=self.main_colour)
        field_wrapper.grid(row=row, column=col, sticky="ew", padx=3, pady=2)

        # Move to next column
        parent._grid_col += 1
        # If column exceeds 1 → go to next row
        if parent._grid_col > 1:
            parent._grid_col = 0
            parent._grid_row += 1

        field_label = tk.Label(
            field_wrapper,
            text=placeholder_text if placeholder_text else "Input Field",
            fg="white",
            bg=self.main_colour,
            font=("Segoe UI", 10, "bold")
        )
        field_label.pack(anchor="w", padx=5, pady=3)

        entry_row = tk.Frame(field_wrapper, bg=self.main_colour)
        entry_row.pack(fill="x", padx=5)

        entry = tk.Entry(entry_row, bg=bg_color, fg="white", insertbackground="white")
        entry.pack(fill="x", padx=5)

        return entry
    def add_field(self):
        self.scrollbar.pack(side="right", fill="y")
        wrapper = tk.Frame(self.scroll_frame, bg=self.main_colour, bd=1, relief="solid", padx=10, pady=10)
        wrapper.pack(fill="x", padx=15, pady=1)

        top_line = tk.Frame(wrapper, bg=self.main_colour)
        top_line.pack(fill="x", pady=2)

        img_label = tk.Label(
            top_line,
            text=f"Enter details of product # "+str(len(self.entries)+1),
            font=("Segoe UI", 10, "bold"),
            fg="#00ffff",
            bg=self.main_colour
        )
        img_label.pack(side="left", anchor="w", pady=2)

        remove_btn = tk.Button(
            top_line,
            text="❌",
            bg="#a83232",
            fg="white",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            command=lambda w=wrapper: self.remove_field(w)
        )
        remove_btn.pack(side="right")
        img_label = tk.Label(
            wrapper,
            text="Enter product Images (You can add up to 10 images)",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#2d2d30"
        )
        #images
        image_box = tk.Frame(wrapper, bg="#2d2d30", bd=2, relief="groove")
        image_box.pack(fill="x", pady=0, padx=3)

        img_title = tk.Label(
            image_box,
            text="Enter product Images (You can add up to 10 images)",
            fg="white",
            bg="#2d2d30",
            font=("Segoe UI", 10, "bold")
        )
        img_title.pack(anchor="w", padx=5, pady=3)

        # Inner wrapper for actual inputs
        image_wrapper = tk.Frame(image_box, bg="#2d2d30")
        image_wrapper.pack(fill="x", padx=5, pady=5)

        # Add image entry + browse + drag&drop
        if image_wrapper not in self.img_arr:
            self.img_arr[image_wrapper]=[]
        add_img_btn = tk.Button(
            image_wrapper,
            text="➕ Add Image",
            bg="#2e8b57",
            fg="white",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        row=len(self.img_arr[image_wrapper])//3
        col=len(self.img_arr[image_wrapper])%3
        add_img_btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        self.add_img_btn[image_wrapper]=add_img_btn
        img_entry,img_row=add_image_box(self,image_wrapper)
        add_img_btn.config(
    command=lambda e=img_entry, r=img_row: browse_image(self, e, r)
)

        #video
        grid_wrapper = tk.Frame(wrapper, bg=self.main_colour)
        grid_wrapper.columnconfigure(0, weight=1)
        grid_wrapper.columnconfigure(1, weight=1)
        grid_wrapper.pack(fill="x", pady=1,padx=3)
        grid_wrapper._grid_row = 0
        grid_wrapper._grid_col = 0
        video_wrapper = tk.Frame(grid_wrapper, bg=self.main_colour)
        video_wrapper.grid(row=grid_wrapper._grid_row, column=grid_wrapper._grid_col, sticky="ew", pady=5, padx=3)
        grid_wrapper._grid_col += 1
        video_label = tk.Label(
            video_wrapper,
            text="Enter product Video",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=self.main_colour
        )
        video_label.pack(anchor="w", padx=5, pady=3)
        video_row = tk.Frame(video_wrapper, bg=self.main_colour)
        video_row.pack(fill="x", padx=5)
        self.allowed_videos = (".mp4", ".mov", ".avi", ".mkv", ".webm")
        video_entry = tk.Entry(video_row, width=55, bg=bg_color, fg="white", insertbackground="white")
        video_entry.pack(side="left", padx=5,pady=5)

        tk.Button(video_row, text="Browse", command=lambda: browse_video(video_entry),
                  bg="#007acc", fg="white", relief="flat").pack(side="left", padx=5)

        drop_label_video = tk.Label(video_row, text="📂 Drag & Drop", fg="#ccc", bg="#2d2d30",
                              font=("Segoe UI", 10, "italic"), width=20, height=2, relief="ridge")
        drop_label_video.pack(side="left", padx=5)
        drop_label_video.drop_target_register(DND_FILES)
        drop_label_video.dnd_bind('<<Drop>>', lambda e, entry=video_entry: handle_drop_video(e, entry))
        #2 x 2 grid
        #title
        title_entry = self.field_design(grid_wrapper,"Enter title of the product")
        #description

        #category
        category_entry = self.field_design(grid_wrapper,"Enter category of the product")
        #location
        location_entry = self.field_design(grid_wrapper,"Enter location of the product")
        #tags
        tags_entry = self.field_design(grid_wrapper,"Enter tags of the product, separated by commas")
        #price
        price_entry = self.field_design(grid_wrapper,"Enter the price of the product")
        price_entry.config(validate="key", validatecommand=(self.register(self.validate_int), "%P"))
        #condition
        condition_entry = self.field_design(grid_wrapper,"Enter condition of the product (e.g., New, Used)")
        #availability
        availability_entry = self.field_design(grid_wrapper,"Enter availability of the product (e.g., In Stock, Single Item)")
        #check boxes
        row = grid_wrapper._grid_row
        col = grid_wrapper._grid_col

        grid3d_wrapper = tk.Frame(grid_wrapper, bg=self.main_colour)
        grid3d_wrapper.grid(row=row, column=col, sticky="ew", pady=5, padx=3)

        # advance grid position (same logic used elsewhere)
# --- place description using grid (don't mix pack/grid inside grid_wrapper) ---
# advance grid position (we already updated _grid_col earlier as needed)
        row = grid_wrapper._grid_row
        col = grid_wrapper._grid_col

        desc_wrapper = tk.Frame(grid_wrapper, bg=self.main_colour)
        desc_wrapper.grid(row=row, column=col, sticky="ew", pady=5, padx=5)

        desc_label = tk.Label(
            desc_wrapper,
            text="Enter description of the product",
            fg="white",
            bg=self.main_colour,
            font=("Segoe UI", 10, "bold")
        )
        desc_label.pack(anchor="w", padx=5, pady=3)

        description_row = tk.Frame(desc_wrapper, bg=self.main_colour)
        description_row.pack(fill="x", padx=5)

        description_entry = tk.Text(description_row, height=3, bg=bg_color, fg="white", insertbackground="white")
        description_entry.pack(fill="x", pady=5, padx=5)

        # move grid position forward (same logic you use elsewhere)
        grid_wrapper._grid_col += 1
        if grid_wrapper._grid_col > 1:
            grid_wrapper._grid_col = 0
            grid_wrapper._grid_row += 1

        # 3-D options — placed in their own grid cell
        grid3d_wrapper = tk.Frame(grid_wrapper, bg=self.main_colour)
        row = grid_wrapper._grid_row
        col = grid_wrapper._grid_col
        grid3d_wrapper.grid(row=row, column=col, sticky="ew", pady=5, padx=3)

        tk.Label(
            grid3d_wrapper,
            text="Other Options",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=self.main_colour
        ).pack(anchor="w", padx=5, pady=3)

        # Checkbox variables (per-field)
        opt_vars = [tk.IntVar(), tk.IntVar(), tk.IntVar()]

        chk_frame = tk.Frame(grid3d_wrapper, bg=self.main_colour)
        chk_frame.pack(fill="x", padx=5, pady=3)

        chk1 = tk.Checkbutton(chk_frame, text="Public meetup", variable=opt_vars[0],
                      bg=self.main_colour, fg="white", selectcolor=self.main_colour, relief="flat",
                      font=("Segoe UI", 10))
        chk1.pack(side="left", padx=6)

        chk2 = tk.Checkbutton(chk_frame, text="Door pickup", variable=opt_vars[1],
                      bg=self.main_colour, fg="white", selectcolor=self.main_colour, relief="flat",
                      font=("Segoe UI", 10))
        chk2.pack(side="left", padx=6)

        chk3 = tk.Checkbutton(chk_frame, text="Door dropoff", variable=opt_vars[2],
                      bg=self.main_colour, fg="white", selectcolor=self.main_colour, relief="flat",
                      font=("Segoe UI", 10))
        chk3.pack(side="left", padx=6)

        # After adding the 3-D widget, advance grid counters the same way if you will add more cells
        grid_wrapper._grid_col += 1
        if grid_wrapper._grid_col > 1:
            grid_wrapper._grid_col = 0
            grid_wrapper._grid_row += 1
        self.entries.append((self.img_arr[image_wrapper], title_entry, description_entry, category_entry, location_entry, tags_entry, price_entry, condition_entry, availability_entry, video_entry, wrapper,opt_vars))
        # self.update_image_numbers()
        # 3-D Grid with three checkboxes

    def remove_field(self, wrapper):
        for entry in self.entries:
            if entry[10] == wrapper:
                self.entries.remove(entry)
                break
        wrapper.destroy()
        if len(self.entries)==0:
            self.scrollbar.pack_forget()
        self.update_image_numbers()
    def update_image_numbers(self):
        for idx, item in enumerate(self.entries, start=1):
            wrapper = item[10]
            for widget in wrapper.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and "Enter details of product #" in child.cget("text"):
                            child.config(text=f"Enter details of product # {idx}")
    # --- File Management ---
    def handle_drop(self, event, entry):
        files = self.tk.splitlist(event.data)
        for file_path in files:
            if os.path.isfile(file_path) and file_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                entry.delete(0, "end")
                entry.insert(0, file_path)
                addImg(self,entry.master,file_path)
    def browse_image(self, entry,img_row):
        file_paths = filedialog.askopenfilenames(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp")]
        )
        if file_paths:

            current = entry.get().strip()
            if current=="":
                entry.delete(0, "end")
                entry.insert(0,file_paths[0])
                addImg(self, img_row, file_paths[0])
            else:
                img_entry, img_row2 = add_image_box(self,img_row.master)
                if  img_entry:
                    img_entry.insert(0, file_paths[0])
                    addImg(self, img_row2, file_paths[0])

            
            for file_path in file_paths[1:]:
                img_entry, img_row2 = add_image_box(self,img_row.master)
                if not img_entry:
                    break
                img_entry.insert(0, file_path)
                addImg(self, img_row2, file_path)

    # --- Bot Run (Threaded) ---
    def validate(self):
        if len(self.entries)==0:
            tk.messagebox.showerror("No Entries", "Please add at least one product entry before running the bot.")
            self.enable_controls()
            return False
        for idx, item in enumerate(self.entries, start=1):
            img_entries, title_entry, description_entry,category_entry, location_entry, tags_entry, price_entry, condition_entry, availability_entry, video_entry ,wrapper,opt_vars= item

            # Print all images
            for img in img_entries:
                if img.get().strip()=="":
                    
                    tk.messagebox.showerror("Missing Image",f"Please provide all image paths for product {idx}.")
                    self.enable_controls()
                    return False
                print(img.get())
            if category_entry.get().strip()=="":
                tk.messagebox.showerror("Missing Category",f"Please provide a category for product {idx}.")
                self.enable_controls()
                return False
            if title_entry.get().strip()=="":
                tk.messagebox.showerror("Missing Title",f"Please provide a title for product {idx}.")
                self.enable_controls()
                return False
            if description_entry.get("1.0", "end").strip() == "":
                tk.messagebox.showerror("Missing Description", f"Please provide a description for product {idx}.")
                self.enable_controls()
                return False
            if location_entry.get().strip()=="":
                tk.messagebox.showerror("Missing Location",f"Please provide a location for product {idx}.")
                self.enable_controls()
                return False
            if tags_entry.get().strip()=="":
                tk.messagebox.showerror("Missing Tags",f"Please provide tags for product {idx}.")
                self.enable_controls()
                return False
            if price_entry.get().strip()=="":
                tk.messagebox.showerror("Missing Price",f"Please provide a price for product {idx}.")
                self.enable_controls()
                return False
            if condition_entry.get().strip()=="":
                tk.messagebox.showerror("Missing Condition",f"Please provide a condition for product {idx}.")
                self.enable_controls()
                return  False
            if availability_entry.get().strip()=="":
                tk.messagebox.showerror("Missing Availability",f"Please provide availability for product {idx}.")
                self.enable_controls()
                return False
        return True
    def get_wait_time(self):
        wait_time = self.waiting_var.get()
        print("Wait time value:", wait_time)
        unit = self.hours_minute_sec_dropdown.get()
        print("Selected unit:", unit)
        if unit == "seconds":
            return wait_time
        elif unit == "minutes":
            return wait_time * 60
        elif unit == "hours":
            return wait_time * 3600
        return wait_time  # default to seconds if something goes wrong   
    def run_bot(self):
        
        self.disable_controls()
        self.status_label.config(text="🤖 Bot is running... Please wait.")

        check=self.validate()
        if not check:
            return
        
        bot_thread = threading.Thread(target=self._run_bot_thread,daemon=True)
        bot_thread.start()
    def run_distribute_bot(self):
        self.disable_controls()
        self.status_label.config(text="🤖 Bot is running... Please wait.")
        check=self.validate()
        if not check:
            return
        bot_thread = threading.Thread(target=self._run_distribute_bot_thread,daemon=True)
        bot_thread.start()
    def _run_distribute_bot_thread(self):
        try:
            time=self.get_wait_time()
            marketplace=self.country_var.get()
            failed_videos = distribute_among_accounts(self.entries,time, marketplace)
            self.after(0, lambda: self.on_bot_complete(failed_videos))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to run bot:\n{e}"))
            self.after(0, self.enable_controls)
    def _run_bot_thread(self):
        try:
            time=self.get_wait_time()
            marketplace=self.country_var.get()
            failed_videos = main(self.entries,time, marketplace)
            self.after(0, lambda: self.on_bot_complete(failed_videos))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to run bot:\n{e}"))
            self.after(0, self.enable_controls)

    def on_bot_complete(self, failed_videos):
        self.enable_controls()
        if failed_videos:
            self.show_failed_dialog(failed_videos)
        else:
            self.status_label.config(text="✅ Bot finished successfully!")
            messagebox.showinfo("Success", "Bot finished successfully! 🎉")

    def disable_controls(self):
        self.add_button.config(state=tk.DISABLED)
        self.renew_btn.config(state=tk.DISABLED)
        self.run_button.config(state=tk.DISABLED)
        self.delete_and_relist_btn.config(state=tk.DISABLED)
        self.distribute_btn.config(state=tk.DISABLED)
        self.run_failed_button.config(state=tk.DISABLED)
        self.save_fields_button.config(state=tk.DISABLED)
        self.load_fields_button.config(state=tk.DISABLED)

    def enable_controls(self):
        self.status_label.config(text="")
        self.add_button.config(state=tk.NORMAL)
        self.renew_btn.config(state=tk.NORMAL)
        self.run_button.config(state=tk.NORMAL)
        self.delete_and_relist_btn.config(state=tk.NORMAL)
        self.distribute_btn.config(state=tk.NORMAL)
        self.run_failed_button.config(state=tk.NORMAL)
        self.save_fields_button.config(state=tk.NORMAL)
        self.load_fields_button.config(state=tk.NORMAL)

    # --- Failed Items ---
    def show_failed_dialog(self, failed_list):
        check=True
        for key in failed_list:
            if len(failed_list[key])!=0:
                check=False
        if check:
            self.status_label.config(text="✅ Bot finished successfully!")
            messagebox.showinfo("Success", "Bot finished successfully! 🎉")
            return
        failed_window = tk.Toplevel(self)
        failed_window.title("❌ Failed generating some product listings")
        failed_window.geometry("600x400")
        failed_window.configure(bg=bg_color)

        tk.Label(failed_window, text="The following product listings failed to generate:",
                 font=("Segoe UI", 12, "bold"), fg="#ff5555", bg=bg_color).pack(pady=10)

        list_frame = tk.Frame(failed_window, bg=bg_color)
        list_frame.pack(fill="both", expand=True, pady=10)

        canvas = tk.Canvas(list_frame, bg=bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner_frame = tk.Frame(canvas, bg=bg_color)

        inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for key in failed_list:
            if len(failed_list[key])==0:
                continue
            tk.Label(inner_frame, text=key+":", font=("Segoe UI", 10), fg="#ffffff", bg=bg_color).pack(anchor="w", padx=20, pady=3)
            for item in failed_list[key]:
                tk.Label(inner_frame, text=item, font=("Segoe UI", 10, "italic"), fg="#cccccc", bg=bg_color, wraplength=550, justify="left").pack(anchor="w", padx=40, pady=3) 

        btn_frame = tk.Frame(failed_window, bg=bg_color)
        btn_frame.pack(pady=15)

        # tk.Button(btn_frame, text="🔁 Regenerate Failed", bg="#2e8b57", fg="white",
        #           font=("Segoe UI", 11, "bold"), relief="flat",
        #           command=lambda: self.regenerate_failed(failed_list, failed_window)).pack(side="left", padx=10)

        tk.Button(btn_frame, text="Close", bg="#a83232", fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat",
                  command=failed_window.destroy).pack(side="left", padx=10)

    def regenerate_failed(self, failed_list, window):
        window.destroy()
        self.clear_entries_ui()
        for img_path, prompt in failed_list:
            self.add_field(img_path)
            self.entries[-1][1].delete(0, "end")
            self.entries[-1][1].insert(0, prompt)
        messagebox.showinfo("Regenerating", "Re-running bot for failed videos...")
        self.run_bot()

    def clear_entries_ui(self):
        self.entries.clear()
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = SceneApp()
    app.mainloop()