from selenium.webdriver.common.by import By
import time
import random
def move_to_path(driver):
    random.seed(int(time.time()))
    try:
        driver.get("https://www.facebook.com")
        time.sleep(random.randint(3,7))
        try:
            marketplace_path = driver.find_element(By.XPATH, "//a[@href='https://www.facebook.com/marketplace/?ref=bookmark']")
            marketplace_path.click()
        except:
            marketplace_path = driver.find_element(By.XPATH, "//a[@href='https://www.facebook.com/marketplace/?ref=bookmark/']")
            marketplace_path.click()
        time.sleep(random.randint(3,7))
        try:
            sell_something_path=driver.find_element(By.XPATH,"//a[@href='/marketplace/create/']")
            sell_something_path.click()
        except:
            sell_something_path=driver.find_element(By.XPATH,"//a[@href='/marketplace/create']")
            sell_something_path.click()
        time.sleep(random.randint(3,7))
        btn = driver.find_element(By.XPATH, "//div[@role='button' and contains(normalize-space(.), 'Item for sale')]")
        btn.click()
        time.sleep(random.randint(3,7))
        return True
    except Exception as e:
        print(f"🚨 Error in move_to_path: {e}")
        return False
def path_to_sell(driver):
    try:
        driver.get("https://www.facebook.com")
        time.sleep(random.randint(3,7))
        try:
            marketplace_path = driver.find_element(By.XPATH, "//a[@href='https://www.facebook.com/marketplace/?ref=bookmark']")
            marketplace_path.click()
        except:
            marketplace_path = driver.find_element(By.XPATH, "//a[@href='https://www.facebook.com/marketplace/?ref=bookmark/']")
            marketplace_path.click()
        time.sleep(random.randint(8,12))
        try:
            dashboard_path=driver.find_element(By.XPATH,"//a[@href='/marketplace/you/selling/']")
            dashboard_path.click()
        except:
            dashboard_path=driver.find_element(By.XPATH,"//a[@href='/marketplace/you/selling']")
            dashboard_path.click()
        time.sleep(random.randint(3,7))
        return True
    except Exception as e:
        return False
def path_to_renew(driver):
    try:
        check=path_to_sell(driver)
        if not check:
            return False
        try:
            dashboard=driver.find_element(By.XPATH,"//a[@href='/marketplace/you/dashboard/']")
            dashboard.click()
        except:
            dashboard=driver.find_element(By.XPATH,"//a[@href='/marketplace/you/dashboard']")
            dashboard.click()
        time.sleep(random.randint(3,7))
        return True
    except Exception as e:
        return False