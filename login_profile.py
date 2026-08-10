import os
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import tkinter as tk
from tkinter import messagebox
import pandas as pd
import multiprocessing

# ---- Browser/session functions ----
def launch_browser(profile_name, stop_event, proxy=None):
    profile_dir = Path(f"profiles/{profile_name}")
    profile_dir.mkdir(parents=True, exist_ok=True)

    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]:
        lock_file = profile_dir / lock_name
        if lock_file.exists():
            try:
                lock_file.unlink()
            except Exception:
                pass

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={str(profile_dir.resolve())}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if proxy and str(proxy).strip() and str(proxy).strip() != "nan":
        options.add_argument(f"--proxy-server={str(proxy).strip()}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://www.facebook.com")
    print(f"Browser [{profile_name}] launched.")

    # Wait until stop_event is triggered
    while not stop_event.is_set():
        stop_event.wait(timeout=1)

    try:
        marker = profile_dir / "First_Login_Done.txt"
        marker.write_text("ok")
    except Exception:
        pass

    try:
        driver.quit()
        print(f"Browser [{profile_name}] closed.")
    except Exception:
        print(f"Browser [{profile_name}] could not close cleanly.")


def make_profile(profiles, stop_event, proxies=None):
    processes = []
    for idx, name in enumerate(profiles):
        px = proxies[idx] if proxies and idx < len(proxies) else None
        p = multiprocessing.Process(target=launch_browser, args=(name, stop_event, px))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


def start_session_control(stop_event):
    root = tk.Tk()
    root.title("Session Control")
    root.geometry("300x110")
    root.resizable(False, False)

    def stop_session():
        stop_event.set()
        root.destroy()

    tk.Label(root, text="Click the button to stop the session.").pack(pady=(12, 6))
    tk.Button(root, text="Stop Session", command=stop_session, width=20).pack(pady=(0, 12))

    root.mainloop()


# ---- Helpers ----
def email_to_safe(email: str, phone: str = "") -> str:
    clean_email = str(email).strip()
    email_safe = clean_email.replace("@", "_at_").replace(".", "_dot_")
    if phone:
        phone_safe = str(phone).strip().replace("+", "_plus_").replace(" ", "_").replace("-", "_")
        return f"{email_safe}_{phone_safe}"
    return email_safe


def load_emails_df():
    if os.path.exists('emails.csv'):
        try:
            df = pd.read_csv('emails.csv', dtype=str).fillna("")
            if 'email' not in df.columns:
                df['email'] = ""
            if 'phone' not in df.columns:
                df['phone'] = ""
            if 'password' not in df.columns:
                df['password'] = ""
            if 'proxy' not in df.columns:
                df['proxy'] = ""
        except Exception:
            df = pd.DataFrame(columns=['email', 'phone', 'password', 'proxy'])
    else:
        df = pd.DataFrame(columns=['email', 'phone', 'password', 'proxy'])

    df['email'] = df['email'].fillna("").astype(str)
    df['phone'] = df['phone'].fillna("").astype(str)
    df['password'] = df['password'].fillna("").astype(str)
    df['proxy'] = df['proxy'].fillna("").astype(str)
    return df

def check_is_logged_in(driver) -> bool:
    """Verifies authentication strictly via Facebook's c_user session cookie."""
    try:
        cookies = driver.get_cookies()
        for c in cookies:
            if c.get('name') == 'c_user' and c.get('value'):
                return True
    except Exception:
        pass
    return False


def is_account_authenticated(email: str, phone: str = "") -> bool:
    safe_email = email_to_safe(email, phone)
    marker = Path(f"profiles/{safe_email}/First_Login_Done.txt")
    return marker.exists()


import time
from selenium.webdriver.common.keys import Keys

def auto_login_session(email: str, password: str = "", proxy: str = "", phone: str = "") -> bool:
    safe_email = email_to_safe(email, phone)
    profile_dir = Path(f"profiles/{safe_email}")
    profile_dir.mkdir(parents=True, exist_ok=True)
    marker = profile_dir / "First_Login_Done.txt"

    # Clean stale lock files if Chrome crashed previously
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]:
        lock_file = profile_dir / lock_name
        if lock_file.exists():
            try:
                lock_file.unlink()
            except Exception:
                pass

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={str(profile_dir.resolve())}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if proxy and str(proxy).strip() and str(proxy).strip() != "nan":
        options.add_argument(f"--proxy-server={str(proxy).strip()}")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://www.facebook.com/login")
        time.sleep(3)

        # Dismiss Cookie consent popup if present
        try:
            cookie_btn = driver.find_element("xpath", "//button[contains(., 'Allow all cookies') or contains(., 'Accept All') or contains(., 'Only allow essential') or contains(., 'Allow essential')]")
            cookie_btn.click()
            time.sleep(1.5)
        except Exception:
            pass

        # Check if already logged in via c_user cookie
        if check_is_logged_in(driver):
            print(f"✅ Account {email} is already authenticated!")
            marker.write_text("ok")
            return True
        else:
            if marker.exists():
                try:
                    marker.unlink()
                except Exception:
                    pass

        # Auto-fill ID & Password using React-compatible setter
        if password and str(password).strip():
            print(f"🔑 Auto-filling credentials for {email}...")
            try:
                # Find Email Box
                email_box = None
                for selector in ["//input[@id='email']", "//input[@name='email']", "//input[@type='text' or @type='email']"]:
                    try:
                        email_box = driver.find_element("xpath", selector)
                        if email_box:
                            break
                    except Exception:
                        pass

                if email_box:
                    try:
                        email_box.click()
                        email_box.send_keys(Keys.CONTROL, 'a')
                        email_box.send_keys(Keys.BACKSPACE)
                    except Exception:
                        pass
                    driver.execute_script("""
                        var el = arguments[0];
                        var val = arguments[1];
                        var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(el, val);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    """, email_box, email)
                    time.sleep(0.5)

                # Find Password Box
                pass_box = None
                for selector in ["//input[@id='pass']", "//input[@name='pass']", "//input[@type='password']"]:
                    try:
                        pass_box = driver.find_element("xpath", selector)
                        if pass_box:
                            break
                    except Exception:
                        pass

                if pass_box:
                    try:
                        pass_box.click()
                        pass_box.send_keys(Keys.CONTROL, 'a')
                        pass_box.send_keys(Keys.BACKSPACE)
                    except Exception:
                        pass
                    driver.execute_script("""
                        var el = arguments[0];
                        var val = arguments[1];
                        var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(el, val);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    """, pass_box, password)
                    time.sleep(0.5)

                # Find & Click Login Button
                login_btn = None
                for selector in ["//button[@name='login']", "//button[@type='submit']", "//button[@id='loginbutton']", "//input[@type='submit']", "//div[@role='button' and contains(., 'Log In')]"]:
                    try:
                        login_btn = driver.find_element("xpath", selector)
                        if login_btn:
                            break
                    except Exception:
                        pass

                if login_btn:
                    login_btn.click()
                    print(f"🚀 Login form submitted for {email}.")
                    time.sleep(4)
            except Exception as ex:
                print(f"Auto-fill error for {email}: {ex}")

        # Poll for successful login (up to 300 seconds / 5 minutes to allow user to complete 2FA / verification)
        print(f"⏳ Monitoring session for {email}. If 2FA or device approval is required, please complete it in the Chrome window...")
        start_time = time.time()
        while time.time() - start_time < 300:
            try:
                if check_is_logged_in(driver):
                    print(f"🎉 Successful login authenticated for {email}!")
                    marker.write_text("ok")
                    return True
            except Exception:
                print(f"Browser closed by user for {email}.")
                break
            time.sleep(2)

        # Final check if user logged in right before timeout or browser close
        if check_is_logged_in(driver):
            print(f"🎉 Login authenticated for {email}!")
            marker.write_text("ok")
            return True

        print(f"⚠️ Login session ended without c_user authentication for {email}.")
        return False
    except Exception as e:
        print(f"Auto login session error for {email}: {e}")
        return False
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


# ---- Main UI ----
def start_main_window():
    df = load_emails_df()
    os.makedirs("profiles", exist_ok=True)

    root = tk.Tk()
    root.title("Profile Manager")
    root.geometry("640x400")
    root.resizable(False, False)

    # Left side frame
    left_frame = tk.Frame(root, padx=12, pady=12)
    left_frame.pack(side="left", fill="y")

    tk.Label(left_frame, text="Manage Profiles", font=("Arial", 12, "bold")).pack(anchor="w")

    tk.Label(left_frame, text="Email:").pack(anchor="w", pady=(8, 2))
    email_entry = tk.Entry(left_frame, width=38)
    email_entry.pack(anchor="w")

    tk.Label(left_frame, text="Phone Number:").pack(anchor="w", pady=(8, 2))
    phone_entry = tk.Entry(left_frame, width=38)
    phone_entry.pack(anchor="w")

    tk.Label(left_frame, text="Proxy (Optional - host:port or http://user:pass@host:port):").pack(anchor="w", pady=(8, 2))
    proxy_entry = tk.Entry(left_frame, width=38)
    proxy_entry.pack(anchor="w")

    # Button frame
    btn_frame = tk.Frame(left_frame, pady=12)
    btn_frame.pack(anchor="w")

    # ---- SAVE PROFILE BUTTON ----
    def on_save_profile():
        nonlocal df
        email_val = email_entry.get().strip()
        phone_val = phone_entry.get().strip()
        proxy_val = proxy_entry.get().strip()

        if not email_val:
            messagebox.showerror("Error", "Email is required.")
            return

        if email_val in df['email'].values:
            # Update existing profile
            df.loc[df['email'] == email_val, 'phone'] = phone_val
            df.loc[df['email'] == email_val, 'proxy'] = proxy_val
        else:
            new_row = {'email': email_val, 'phone': phone_val, 'proxy': proxy_val}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        df.to_csv('emails.csv', index=False)

        safe_email = email_to_safe(email_val, phone_val)
        profile_dir = Path("profiles") / safe_email
        profile_dir.mkdir(parents=True, exist_ok=True)

        refresh_listbox()
        messagebox.showinfo("Saved", f"Profile '{email_val}' saved successfully!")

    save_btn = tk.Button(btn_frame, text="Save Profile", command=on_save_profile,
                         width=16, bg="#4CAF50", fg="white")
    save_btn.pack(side="left", padx=(0, 8))

    # ---- START SELECTED BUTTON ----
    def on_start_selected():
        sel = profiles_listbox.curselection()
        if not sel:
            messagebox.showwarning("Warning", "Select a saved profile first.")
            return

        idx = sel[0]
        selected_email = profiles_listbox.get(idx)
        phone_row = df.loc[df['email'] == selected_email, 'phone'].values
        phone_val = phone_row[0] if len(phone_row) > 0 else ""
        proxy_row = df.loc[df['email'] == selected_email, 'proxy'].values
        proxy_val = proxy_row[0] if len(proxy_row) > 0 else ""

        safe_email = email_to_safe(selected_email, phone_val)
        profile_dir = Path("profiles") / safe_email
        profile_dir.mkdir(parents=True, exist_ok=True)

        manager = multiprocessing.Manager()
        stop_event = manager.Event()

        ui_proc = multiprocessing.Process(target=start_session_control, args=(stop_event,))
        ui_proc.start()

        make_profile([safe_email], stop_event, proxies=[proxy_val])
        ui_proc.join()

        messagebox.showinfo("Done", f"Session for '{selected_email}' finished.")

    start_sel_btn = tk.Button(btn_frame, text="Start Selected", command=on_start_selected,
                              width=16, bg="#2196F3", fg="white")
    start_sel_btn.pack(side="left", padx=(0, 8))

    # Right frame (listbox + delete)
    right_frame = tk.Frame(root, padx=12, pady=12)
    right_frame.pack(side="right", fill="both", expand=True)

    tk.Label(right_frame, text="Saved Profiles", font=("Arial", 12, "bold")).pack(anchor="w")

    listbox_frame = tk.Frame(right_frame)
    listbox_frame.pack(fill="both", expand=True, pady=(6, 4))

    scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
    profiles_listbox = tk.Listbox(listbox_frame, width=38, height=12, yscrollcommand=scrollbar.set, exportselection=False)
    scrollbar.config(command=profiles_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    profiles_listbox.pack(side="left", fill="both", expand=True)

    def refresh_listbox():
        nonlocal df
        df = load_emails_df()
        profiles_listbox.delete(0, tk.END)
        for e in df['email'].tolist():
            profiles_listbox.insert(tk.END, e)

    refresh_listbox()

    def on_listbox_select(event):
        sel = profiles_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        selected_email = profiles_listbox.get(idx)
        pw = df.loc[df['email'] == selected_email, 'phone'].values
        pw = pw[0] if len(pw) > 0 else ""
        px = df.loc[df['email'] == selected_email, 'proxy'].values
        px = px[0] if len(px) > 0 else ""

        email_entry.delete(0, tk.END)
        email_entry.insert(0, selected_email)
        phone_entry.delete(0, tk.END)
        phone_entry.insert(0, pw)
        proxy_entry.delete(0, tk.END)
        proxy_entry.insert(0, px)

    profiles_listbox.bind('<<ListboxSelect>>', on_listbox_select)

    # ---- DELETE BUTTON ----
    def on_delete_profile():
        nonlocal df
        sel = profiles_listbox.curselection()
        if not sel:
            messagebox.showwarning("Warning", "Select a profile to delete.")
            return

        idx = sel[0]
        selected_email = profiles_listbox.get(idx)
        phone_row = df.loc[df['email'] == selected_email, 'phone'].values
        phone_val = phone_row[0] if len(phone_row) > 0 else ""

        answer = messagebox.askyesno("Confirm Delete",
                                     f"Delete profile '{selected_email}'?\nThis will remove its entry and folder.")
        if not answer:
            return

        df = df[df['email'] != selected_email].reset_index(drop=True)
        df.to_csv('emails.csv', index=False)

        profile_dir = Path("profiles") / email_to_safe(selected_email, phone_val)
        try:
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not delete folder {profile_dir}: {e}")

        refresh_listbox()
        email_entry.delete(0, tk.END)
        phone_entry.delete(0, tk.END)
        proxy_entry.delete(0, tk.END)
        messagebox.showinfo("Deleted", f"Profile '{selected_email}' deleted.")

    delete_btn = tk.Button(right_frame, text="Delete Profile", command=on_delete_profile,
                           width=18, bg="#f44336", fg="white")
    delete_btn.pack(pady=(6, 0), anchor="w")

    info_label = tk.Label(right_frame,
        text="Click a profile to autofill details.\nUse Save Profile to add or update.",
        justify="left")
    info_label.pack(anchor="w", pady=(8, 0))

    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support() 
    start_main_window()
