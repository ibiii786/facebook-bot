import os
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from Open_fb import email_to_safe, read_multiple_credentials
from path import path_to_renew
import multiprocessing
import random
CSV_PATH = "emails.csv"
import time
def worker(nums,driver):
    seed=int(time.time())
    random.seed(seed)
    time.sleep(random.randint(5,10))
    renew_box = driver.find_element(
    "xpath", 
    "//a[contains(@href, '/marketplace/selling/renew_listings/?is_routable_dialog=true')]"
)

    renew_box.click()
    time.sleep(random.randint(5,10))
    renew_buttons = driver.find_elements("xpath", "//div[@role='button' and contains(normalize-space(.), 'Renew')]")
    idx=0
    outside_boxes = driver.execute_script(
        "return Array.from(document.querySelectorAll('div')).filter(d => "
        "window.getComputedStyle(d).overflowY === 'auto');"
    )
    box = None
    for outside_box in outside_boxes:
        try:
            outside_box.click()
            box=outside_box
            break
        except:
            pass
    completed=0
    while idx < nums and idx < len(renew_buttons):
        try:
            renew_buttons = driver.find_elements("xpath", "//div[@role='button' and contains(normalize-space(.), 'Renew')]")
            renew_buttons[idx].click()
            time.sleep(3)
            print(f"Renewed item {idx+1}")
            # scroll the container down to load more items
            
            if completed != 0 and (completed)%5==0:
                print("Scrolling down to load more items...")
                if box:
                    try:
                        driver.execute_script("arguments[0].scrollTop += 150", box)
                    except Exception:
                        pass
            if completed !=0 and (completed+1)%20==0:
                driver.refresh()
                time.sleep(random.randint(10,15))
                
                outside_boxes = driver.execute_script(
        "return Array.from(document.querySelectorAll('div')).filter(d => "
        "window.getComputedStyle(d).overflowY === 'auto');"
    )
                box = None
                for outside_box in outside_boxes:
                    try:
                        outside_box.click()
                        box=outside_box
                        break
                    except:
                        pass
                idx=-1
                nums-=20
            time.sleep(random.randint(1,3))

            idx+=1
            completed+=1
        except Exception as e:
            print(f"Error renewing item {idx+1}: {e}")
            idx+=1
            nums+=1

def delete_and_relist_worker(driver,nums):
    time.sleep(random.randint(5,10))
    renew_box = driver.find_element(
    "xpath", 
    "//a[contains(@href, '/marketplace/selling/relist_items/?is_routable_dialog=true&show_only_delete_and_relist=true')]"
)
    renew_box.click()
    time.sleep(random.randint(5,10))
    relist_buttons = driver.find_elements("xpath", "//div[@role='button' and (contains(normalize-space(.), 'Delete & relist') or contains(normalize-space(.), 'Delete and Relist'))]")
    idx=0
    outside_boxes = driver.execute_script(
        "return Array.from(document.querySelectorAll('div')).filter(d => "
        "window.getComputedStyle(d).overflowY === 'auto');"
    )
    box = None
    for outside_box in outside_boxes:
        try:
            outside_box.click()
            box=outside_box
            break
        except :
            pass
    completed=0
    while idx < nums and idx < len(relist_buttons):
        try:
            relist_buttons[idx].click()
            time.sleep(random.randint(3,7))
            confirm_button = driver.find_element("xpath", "//div[@role='button' and contains(normalize-space(.), 'Delete and Relist')]")
            confirm_button.click()
            time.sleep(random.randint(5,10))
            print(f"Deleted and relisted item {idx+1}")
            completed+=1
            if completed != 0 and (completed)%5==0:
                print("Scrolling down to load more items...")
                if box:
                    try:
                        driver.execute_script("arguments[0].scrollTop += 150", box)
                    except Exception:
                        pass
            time.sleep(random.randint(1,3))
            if completed !=0 and (completed+1)%20==0:
                driver.refresh()
                time.sleep(random.randint(5,10))
                idx=-1
                nums-=20
            relist_buttons = driver.find_elements("xpath", "//div[@role='button' and (contains(normalize-space(.), 'Delete & relist') or contains(normalize-space(.), 'Delete and Relist'))]")
            idx+=1
        except Exception as e:
            print(f"Error deleting and relisting item {idx+1}: {e}")
            idx+=1
            nums+=1

def renew_worker(nums, email, proxy=None):    
    safe_email = email_to_safe(email)
    base_profile_dir = Path("profiles")
    profile_dir = base_profile_dir / safe_email
    profile_dir.mkdir(parents=True, exist_ok=True)
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
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        check = path_to_renew(driver)
        if not check:
            print("Could not navigate to renew path, going directly to dashboard")
            driver.get("https://www.facebook.com/marketplace/you/dashboard")
        worker(nums, driver)
    except Exception as e:
        print(f"Error in renew_worker for {email}: {e}")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

def renew_and_relist(nums, email, proxy=None):
    safe_email = email_to_safe(email)
    base_profile_dir = Path("profiles")
    profile_dir = base_profile_dir / safe_email
    profile_dir.mkdir(parents=True, exist_ok=True)
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
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        check = path_to_renew(driver)
        if not check:
            print("Could not navigate to renew path, going directly to dashboard")
            driver.get("https://www.facebook.com/marketplace/you/dashboard")
        delete_and_relist_worker(driver, nums)
    except Exception as e:
        print(f"Error in renew_and_relist for {email}: {e}")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

def main(nums, call="renew"):
    accounts = []
    if os.path.exists(CSV_PATH):
        accounts = read_multiple_credentials(CSV_PATH)
    for account in accounts:
        email = account[0]
        proxy = account[2] if len(account) > 2 else None
        if call == "relist":
            renew_and_relist(nums, email, proxy=proxy)
        else:
            p = multiprocessing.Process(target=renew_worker, args=(nums, email, proxy))
            p.start()
            p.join()

if __name__ == "__main__":
    multiprocessing.freeze_support()