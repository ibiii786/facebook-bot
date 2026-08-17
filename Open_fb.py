import os
import pandas as pd
from pathlib import Path
from requests import options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from Automation import go_to_items
from login_profile import email_to_safe
from path import move_to_path
import time
from save_state import make_files,set_file_status
CSV_PATH = "emails.csv"
saved_states_file = "saved_states.csv"
def automation_worker(email, entries, list_location, marketplace_location="UK", proxy=None, wait_for_review=False):
    n_generated = []
    driver = None
    keep_browser_open = False
    try:      
        safe_email = email_to_safe(email)
        base_profile_dir = Path("profiles")
        profile_dir = base_profile_dir / safe_email
        profile_dir.mkdir(parents=True, exist_ok=True)
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
        if proxy and str(proxy).strip() and str(proxy).strip() != "nan":
            options.add_argument(f"--proxy-server={str(proxy).strip()}")
        service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # === Login or reuse session ===
        marker = profile_dir / "First_Login_Done.txt"
        if not marker.exists():
            raise Exception("Email not logged in yet.")
        else:
            print(f"♻️ Reusing existing session for {email}")
            check = move_to_path(driver)
            if not check:
                print(f"🚨 Could not navigate to marketplace for {email}")
                driver.get("https://www.facebook.com/marketplace/create/item")
            else:
                driver.refresh()
            for (img_entries, title_entry, description_entry, category_entry, location_entry, tags_entry, price_entry, condition_entry, availability_entry, video_entry, wrapper, opt_vars) in entries:
                title = title_entry.get()
                price = price_entry.get()
                category = category_entry.get()
                condition = condition_entry.get()
                description = description_entry.get("1.0", "end").strip()
                availability = availability_entry.get()
                product_tags = [tag for tag in tags_entry.get().split(",")]
                images = [img.get() for img in img_entries]
                video = video_entry.get().strip()
                time.sleep(7)
                check = go_to_items(driver, title, price, category, condition, description, availability, product_tags, list_location, images, video, opt_vars[0].get(), opt_vars[1].get(), opt_vars[2].get(), marketplace_location, wait_for_review)
                if check == "REVIEW_STUCK":
                    n_generated.append(f"{title} (⚠️ Stuck in Review - Browser Open)")
                    keep_browser_open = True
                elif not check:
                    n_generated.append((title))
                else:
                    set_file_status(title, email)
    except Exception as e:
        for (img_entries, title_entry, description_entry, category_entry, location_entry, tags_entry, price_entry, condition_entry, availability_entry, video_entry, wrapper, opt_vars) in entries:
            title = title_entry.get()
            n_generated.append((title))
        print(f"🚨 Error in automation_worker for {email}: {e}")

    finally:
        if driver is not None and not keep_browser_open:
            try:
                driver.quit()
            except Exception:
                pass
    return n_generated

def read_multiple_credentials(path=CSV_PATH):
    """Read email/phone/proxy records from a CSV file."""
    if not os.path.exists(path):
        return []

    creds = []
    try:
        data = pd.read_csv(path, dtype=str).fillna("")
        for row in data.itertuples(index=False):
            email = getattr(row, 'email', '')
            phone = getattr(row, 'phone', '')
            proxy = getattr(row, 'proxy', '') if hasattr(row, 'proxy') else ''
            creds.append((email, phone, proxy))
    except Exception as e:
        print(f"Error reading credentials CSV: {e}")
    return creds

def distribute_among_accounts(entries, time_sleep=1800, marketplace_location="UK", wait_for_review=False):
    not_gen_overall = {}

    if not os.path.exists(CSV_PATH):
        return []

    accounts = read_multiple_credentials(CSV_PATH)
    if not accounts:
        return []

    # Distribute entries as contiguous chunks (equal as possible)
    n_accounts = len(accounts)
    n_entries = len(entries)
    entries_per_account = n_entries // n_accounts
    remainder = n_entries % n_accounts

    assignments = []
    i = 0
    for idx, account in enumerate(accounts):
        take = entries_per_account + (1 if idx < remainder else 0)
        assigned = entries[i:i+take] if take > 0 else []
        assignments.append((account, assigned))
        i += take

    # Process in round-robin: first entry of each account, then second entry of each, ...
    if os.path.exists(saved_states_file):
        os.remove(saved_states_file)
    pd.DataFrame(columns=["Name", "Status", "Title", "Price", "Category", "Condition", "Description", "Availability", "Product_Tags", "Images", "Video", "public_meetup", "door_dropoff", "door_meetup", "Location","Market_Location"]).to_csv(saved_states_file, index=False)
    max_len = max((len(a[1]) for a in assignments), default=0)
    for j in range(max_len):
        for account, assigned in assignments:
            if j < len(assigned):
                entry = assigned[j]
                make_files(entry, account[0], entry[4].get(), marketplace_location)
    j = 0
    for j in range(max_len):
        for account, assigned in assignments:
            if j < len(assigned):
                entry = assigned[j]
                try:
                    if account[0] not in not_gen_overall:
                        not_gen_overall[account[0]] = []
                    proxy = account[2] if len(account) > 2 else None
                    result = automation_worker(account[0], [entry], entry[4].get(), marketplace_location, proxy=proxy, wait_for_review=wait_for_review)
                    if result:
                        not_gen_overall[account[0]].extend(result)
                except Exception as e:
                    print(f"🚨 Error running automation for {account[0]} on round {j}: {e}")
        # wait time_sleep seconds after completing one round across all accounts
        time.sleep(time_sleep)

    return not_gen_overall

def _interruptible_sleep(seconds, stop_event):
    """Sleep in small increments so a stop_event can interrupt long waits.
    Returns False if a stop was requested, True if the full sleep completed."""
    if stop_event is None:
        time.sleep(seconds)
        return True
    end = time.time() + seconds
    while time.time() < end:
        if stop_event is not None and stop_event.is_set():
            return False
        time.sleep(min(1, end - time.time()))
    return True

def main(entries, time_sleep=1800, wait_time_accounts=2, marketplace_location="UK", wait_for_review=False, stop_event=None):
    not_gen = {}
    if os.path.exists(CSV_PATH):
        accounts = read_multiple_credentials(CSV_PATH)
    else:
        accounts = []
    entry_idx = 0
    if os.path.exists(saved_states_file):
        os.remove(saved_states_file)
    pd.DataFrame(columns=["Name", "Status", "Title", "Price", "Category", "Condition", "Description", "Availability", "Product_Tags", "Images", "Video", "public_meetup", "door_dropoff", "door_meetup", "Location", "Market_Location"]).to_csv(saved_states_file, index=False)

    for entry_idx in range(len(entries)):
        location = entries[entry_idx][4].get()
        location_list = location.split("|")
        idx = 0
        for account in accounts:
            if idx >= len(location_list):
                idx = 0
            make_files(entries[entry_idx], str(account[0]), location_list[idx], marketplace_location)
            idx += 1

    for entry_idx in range(len(entries)):
        if stop_event is not None and stop_event.is_set():
            print("🛑 Stop requested — halting before next entry.")
            return not_gen

        location = entries[entry_idx][4].get()
        location_list = location.split("|")
        idx = 0
        for account in accounts:
            if stop_event is not None and stop_event.is_set():
                print("🛑 Stop requested — halting before next account.")
                return not_gen

            try:
                if account[0] not in not_gen:
                    not_gen[account[0]] = []
                if idx >= len(location_list):
                    idx = 0
                proxy = account[2] if len(account) > 2 else None
                result = automation_worker(account[0], [entries[entry_idx]], location_list[idx], marketplace_location, proxy=proxy, wait_for_review=wait_for_review)
                if result:
                    not_gen[account[0]].extend(result)
            except Exception as e:
                print(f"🚨 Error running automation for {account[0]}: {e}")

            print("Waiting")
            if not _interruptible_sleep(wait_time_accounts, stop_event):
                print("🛑 Stop requested during wait — halting.")
                return not_gen
            print("Starting Again")
            idx += 1

        if not _interruptible_sleep(time_sleep, stop_event):
            print("🛑 Stop requested during round wait — halting.")
            return not_gen

    return not_gen
        
if __name__ == "__main__":
    main()