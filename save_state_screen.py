import ast
import tkinter as tk
from tkinter import ttk
import pandas as pd
from login_profile import email_to_safe
from Automation import go_to_items
from path import move_to_path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path
from save_state import set_file_status
save_state_file = "saved_states.csv"
import threading
import os
import tkinter.messagebox as messagebox
bg_color = "#1e1e1e"
def get_failed_fields():
    if not os.path.exists(save_state_file):
        return []
    df = pd.read_csv(save_state_file)
    print(df,"FILE IS READ OVER HERE")
    failed_rows = df[df['Status'] == False]
    failed_fields_list = []
    for index, row in failed_rows.iterrows():
        failed_fields = {
            "Email": row['Name'].split("||||")[1] if '||||' in row['Name'] else row['Name'],
            "Title": row['Title'],
            "Price": row['Price'],
            "Category": row['Category'],
            "Condition": row['Condition'],
            "Description": row['Description'],
            "Availability": row['Availability'],
            "Product_Tags": row['Product_Tags'],
            "Images": row['Images'],
            "Video": row['Video'],
            "Location": row['Location'],
            "Public_Meetup": bool(row['public_meetup']),
            "Door_Dropoff": bool(row['door_dropoff']),
            "Door_Meetup": bool(row['door_meetup']),
            "Marketplace": row["Market_Location"]
        }
        failed_fields_list.append(failed_fields)
    return failed_fields_list
def main():
    global df
    # keep only rows where Status is False
    global working_label
    # ensure Video column exists and replace nulls with empty string    
    global root
    root = tk.Tk()
    root.title("Save State Screen")
    root.geometry("900x600")
    root.configure(bg=bg_color)  
    working_label = tk.Label(root,text="🤖 Running bot... Please wait.", bg=bg_color, fg="white", font=("Helvetica", 12))
    working_label.pack_forget()
    if not os.path.exists(save_state_file):
        working_label.pack(pady=10)
        working_label.config(text="No saved state found.")
        root.mainloop()
        return

    df = pd.read_csv(save_state_file)
    if 'Video' not in df.columns:
        df['Video'] = ''
    else:
        df['Video'] = df['Video'].fillna('')
    df = df[df['Status'] == False].copy()
    for col in ["Images", "Product_Tags"]:
        df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else [])
    print(len(df["Product_Tags"]))
    print(df["Product_Tags"])
    # Top button frame
    buttons_frame = tk.Frame(root, bg=bg_color)
    buttons_frame.pack(pady=20)
    global run_button
    run_button = tk.Button(
        buttons_frame, text="Run bot on given data", 
        command=lambda:threading.Thread(target=run_bot,daemon=True).start(), bg="#4CAF50", fg="white",
        font=("Helvetica", 12, "bold"), padx=10, pady=5
    )
    run_button.pack()

    # Frame to hold states
    states_frame = tk.Frame(root, bg=bg_color)
    states_frame.pack(pady=10, fill="both", expand=True)

    # Add a canvas + scrollbar
    canvas = tk.Canvas(states_frame, bg=bg_color, bd=0, highlightthickness=0, relief="flat")
    scrollbar = tk.Scrollbar(
        states_frame,
        orient="vertical",
        command=canvas.yview,
        bd=0,
        relief="flat",
        highlightthickness=0,
        troughcolor=bg_color,
        bg=bg_color,
        activebackground=bg_color
    )
    scrollable_frame = tk.Frame(canvas, bg=bg_color, bd=0, highlightthickness=0)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Create frames for each row
    global main_grid
    main_grid=tk.Frame(scrollable_frame, bg=bg_color)
    main_grid.grid_columnconfigure(0, weight=1)
    main_grid.grid_rowconfigure(0, weight=1)
    main_grid.pack(pady=10, padx=10, fill="both", expand=True)
    create_states(main_grid,df)

    root.mainloop()
def create_states(main_grid,df):
    global states
    states=[]
    row_idx=0
    column=0
    for index, row in df.iterrows():
        state_frame = tk.Frame(
            main_grid, borderwidth=1, relief="solid", bg=bg_color
        )
        state_frame.grid(row=row_idx, column=column, sticky="ew", padx=10, pady=5)
        column += 1
        if column >= 3:
            column = 0
            row_idx += 1
        print(len(row['Images'][0]))
        if len(row['Description'])>30:
            row['Description'] = row['Description'][:20] + "..."
        first_name = row['Name']
        name=first_name.split("||||")[1] if '||||' in first_name else first_name
        name_display = name if len(name) < 30 else name[:20] + "..."
        title_val = row['Title']
        title_display = title_val if len(title_val) < 30 else title_val[:20] + "..."
        price_val = row['Price']
        cat_val = row['Category']
        cond_val = row['Condition']
        desc_val = row['Description']
        desc_display = desc_val if len(desc_val) < 30 else desc_val[:20] + "..."
        avail_val = row['Availability']
        tags_val = row['Product_Tags']
        tags_display = tags_val if len(tags_val) <= 0 else str(tags_val[0]) + "..."
        images_val = row['Images']
        img_first = images_val[0] if images_val else ""
        img_display = img_first if len(img_first) < 30 else img_first[:20] + "..."
        loc_val = row['Location']
        pub_meetup = bool(row['public_meetup'])
        door_drop = bool(row['door_dropoff'])
        door_meet = bool(row['door_meetup'])
        market_loc = row["Market_Location"]
        label_lines = [
            f"Email: {name_display}",
            f"Title: {title_display}",
            f"Price: {price_val}",
            f"Category: {cat_val}",
            f"Condition: {cond_val}",
            f"Description: {desc_display}",
            f"Availability: {avail_val}",
            f"Product Tags: {tags_display}",
            f"Images: {img_display}",
            f"Location: {loc_val}",
            f"Public Meetup: {pub_meetup}",
            f"Door Dropoff: {door_drop}",
            f"Door Meetup: {door_meet}",
            f"Marketplace: {market_loc}"
        ]

        # Only add Video if it's not empty
        video_val = row['Video']
        if str(video_val).strip():
            label_lines.insert(8, f"Video: {video_val}")  # after Images

        label_text = "\n".join(label_lines)
        label = tk.Label(state_frame, text=label_text, justify="left", anchor="w", bg=bg_color, fg="white")
        label.pack(side="left", padx=10)

        # Delete button
        def make_delete_callback(r, f=state_frame):
            def delete_state():
                global df
                df = df[df['Name'] != r['Name']]
                f.destroy()
            return delete_state

        delete_button = tk.Button(
            state_frame, text="Delete", command=make_delete_callback(row),
            bg="#f44336", fg="white", font=("Helvetica", 10, "bold"), padx=5, pady=3
        )
        delete_button.pack(side="right", padx=10)
        states.append(state_frame)

def run_bot():
    # working_label.pack(pady=10)
    # global df,run_button
    # run_button.config(state=tk.DISABLED)
    global df
    import os
    if os.path.exists(save_state_file):
        df = pd.read_csv(save_state_file)
        if 'Video' not in df.columns:
            df['Video'] = ''
        else:
            df['Video'] = df['Video'].fillna('')
        df = df[df['Status'] == False].copy()
        for col in ["Images", "Product_Tags"]:
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else [])
        os.remove(save_state_file)
    df.to_csv(save_state_file, index=False)  
    print(df)    
    
    for index, row in df.iterrows():
        driver=None
        print("FAILED BOT STARTED")
        try:
            first_name = row['Name']
            email = first_name.split("||||")[1] 
            print(f"Processing for {email}")
            safe_email = email_to_safe(email)
            title = row['Title']
            price = row['Price']
            category = row['Category']
            condition = row['Condition']
            description = row['Description']
            availability = row['Availability']
            product_tags = row['Product_Tags']
            images = row['Images']
            video = row['Video']
            location = row['Location']
            public_meetup = row['public_meetup']
            door_dropoff = row['door_dropoff']
            door_meetup = row['door_meetup']
            print(product_tags)
            check=False
            safe_email = email_to_safe(email)
            base_profile_dir = Path("profiles")
            profile_dir = base_profile_dir / safe_email
            profile_dir.mkdir(parents=True, exist_ok=True)
            # === Download directory setup ===
            # === Chrome setup ===
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument(f"--user-data-dir={str(profile_dir.resolve())}")
            options.add_argument("--profile-directory=Default")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            # options.add_argument("--headless=new")
            service = Service(ChromeDriverManager().install())
            # === Stage 1: Wait for previous Chrome to open ===
            driver = webdriver.Chrome(service=service, options=options)
            check=False
            check=move_to_path(driver)
            if not check:
                print(f"🚨 Could not navigate to marketplace for {email}")
                driver.get("https://www.facebook.com/marketplace/create/item")
            else:
                driver.refresh()
            
            check=go_to_items(driver, title, price, category, condition, description, availability, product_tags, location, images, video,public_meetup,door_dropoff,door_meetup,marketplace_location=row['Market_Location'])
            if not check:
                print(f"🚨 Could not post item for {email}")
            else:
                set_file_status(title, email)
        except Exception as e:
            print(f"🚨 An error occurred for {email}: {e}")
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
        
    def _ui_finish():
        for state in states:
            try:
                state.destroy()
            except Exception:
                pass
        df_remaining = pd.read_csv(save_state_file) if os.path.exists(save_state_file) else pd.DataFrame()
        if not df_remaining.empty and 'Status' in df_remaining.columns:
            df_remaining = df_remaining[df_remaining['Status'] == False].copy()
        create_states(main_grid, df_remaining)
        working_label.pack_forget()
        run_button.config(state=tk.NORMAL)
        messagebox.showinfo("Info", "Bot run completed.")

    if 'root' in globals() and root:
        root.after(0, _ui_finish)