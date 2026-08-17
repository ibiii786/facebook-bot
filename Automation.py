import sys
import random
import time
import threading
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from selenium.webdriver.common.keys import Keys
import pyperclip
from Assets.Utils.ImageHandling.Handle_image import anti_fingerprint_image

_paste_lock = threading.Lock()

PROHIBITED_KEYWORDS = [
    "replica", "fake", "first copy", "counterfeit", "master copy", 
    "weapon", "gun", "tobacco", "vape", "cbd", "prescription", "stolen"
]

def check_policy_keywords(title, description, price):
    text = f"{title} {description}".lower()
    found = [word for word in PROHIBITED_KEYWORDS if word in text]
    if found:
        print(f"⚠️ POLICY WARNING: Prohibited keywords detected in listing '{title}': {found}")
    try:
        p_val = float(str(price).replace("$", "").replace("£", "").strip())
        if p_val == 0 or p_val == 1:
            print(f"⚠️ POLICY WARNING: Suspicious $0/$1 bait price detected for listing '{title}'.")
    except Exception:
        pass

def safe_paste(driver, element, text):
    """
    Thread-safe human-mimicking text input.
    Uses native OS clipboard paste and human keystroke simulation to ensure
    all input events carry `isTrusted: true` and avoid Meta's anti-bot synthetic event triggers.
    """
    with _paste_lock:
        try:
            # 1. Focus element
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(random.uniform(0.2, 0.4))
            element.click()
            time.sleep(random.uniform(0.2, 0.4))

            # 2. Clear existing text with native keyboard commands
            element.send_keys(Keys.CONTROL, 'a')
            time.sleep(0.1)
            element.send_keys(Keys.BACKSPACE)
            time.sleep(0.15)

            # 3. Paste via native OS clipboard
            pyperclip.copy(str(text))
            time.sleep(0.1)
            element.send_keys(Keys.CONTROL, 'v')
            time.sleep(random.uniform(0.4, 0.7))

            # 4. Verify text stuck properly
            current_val = element.get_attribute("value") or ""
            if not current_val.strip() and str(text).strip():
                # Fallback: Type with human-paced keystrokes
                print("Clipboard paste fallback: typing with human keystroke intervals...")
                element.click()
                for char in str(text):
                    element.send_keys(char)
                    time.sleep(random.uniform(0.02, 0.06))

        except Exception as e:
            print(f"Safe paste error: {e}")
            try:
                pyperclip.copy(str(text))
                element.send_keys(Keys.CONTROL, 'a')
                element.send_keys(Keys.CONTROL, 'v')
            except Exception:
                element.send_keys(str(text))


def check_scrollable_elements(driver):
    """Check and return all elements that can be scrolled"""
    try:
        scrollable_elements = driver.execute_script("""
            function getElementXPath(element) {
                if (element.id) {
                    return 'id("' + element.id + '")';
                }
                const parts = [];
                while (element && element.nodeType === Node.ELEMENT_NODE) {
                    let index = 1;
                    let sibling = element.previousSibling;
                    while (sibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === element.nodeName) {
                            index++;
                        }
                        sibling = sibling.previousSibling;
                    }
                    const tagName = element.nodeName.toLowerCase();
                    parts.unshift(tagName + '[' + index + ']');
                    element = element.parentNode;
                }
                return parts.length ? '/' + parts.join('/') : '';
            }
            const scrollableElements = [];
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                const hasVerticalScroll = el.scrollHeight > el.clientHeight;
                const hasHorizontalScroll = el.scrollWidth > el.clientWidth;
                const overflowY = window.getComputedStyle(el).overflowY;
                const overflowX = window.getComputedStyle(el).overflowX;
                
                if ((hasVerticalScroll && (overflowY === 'auto' || overflowY === 'scroll')) ||
                    (hasHorizontalScroll && (overflowX === 'auto' || overflowX === 'scroll'))) {
                    scrollableElements.push({
                        tag: el.tagName,
                        id: el.id,
                        class: el.className,
                        xpath: getElementXPath(el),
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight,
                        scrollWidth: el.scrollWidth,
                        clientWidth: el.clientWidth,
                        hasVerticalScroll: hasVerticalScroll,
                        hasHorizontalScroll: hasHorizontalScroll
                    });
                }
            });
            return scrollableElements;
        """)
        print(f"Found {len(scrollable_elements)} scrollable elements:")
        for i, el in enumerate(scrollable_elements):
            print(f"{i+1}. xpath={el.get('xpath', '')}, tag={el.get('tag', '')}, id={el.get('id', '')}, class={el.get('class', '')}")
        return scrollable_elements
    except Exception as e:
        print(f"Error checking scrollable elements: {e}")
def wait_for_media_upload(driver, max_wait=90):
    """Waits for image/video upload processing and spinner indicators to disappear."""
    print("⏳ Waiting for media (images/videos) to finish uploading...")
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # Check for loading progress indicators or spinners in Facebook DOM
            spinners = driver.find_elements("xpath", "//*[@role='progressbar'] | //*[contains(@aria-label, 'Loading')] | //*[contains(@class, 'progress')]")
            active_spinners = [s for s in spinners if s.is_displayed()]
            
            # Check if Next button has become active (not aria-disabled="true")
            next_btns = driver.find_elements("xpath", "//div[@role='button' and (normalize-space(.)='Next' or contains(@aria-label, 'Next'))]")
            ready = False
            for btn in next_btns:
                if btn.is_displayed() and btn.get_attribute("aria-disabled") != "true":
                    ready = True
                    break
            
            if ready and len(active_spinners) == 0:
                elapsed = int(time.time() - start_time)
                print(f"✅ Media upload completed and Next button enabled after {elapsed}s.")
                return True
        except Exception:
            pass

        time.sleep(2)

    elapsed = int(time.time() - start_time)
    print(f"⌛ Media wait timeout after {elapsed}s. Proceeding to click Next...")
    return False


def find_and_click_button(driver, label_names, timeout=60):
    """Finds and clicks a button by flexible XPaths and labels, handling aria-disabled and JS click fallbacks."""
    start = time.time()
    while time.time() - start < timeout:
        for label in label_names:
            xpaths = [
                f"//div[@role='button' and (normalize-space(.)='{label}' or contains(@aria-label, '{label}'))]",
                f"//div[@aria-label='{label}']",
                f"//button[normalize-space(.)='{label}' or contains(@aria-label, '{label}')]",
                f"//span[normalize-space(text())='{label}']/ancestor::div[@role='button']",
                f"//span[normalize-space(text())='{label}']/ancestor::button",
                f"//*[self::div or self::button or self::span][@role='button' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label.lower()}')]"
            ]
            for xpath in xpaths:
                try:
                    elements = driver.find_elements("xpath", xpath)
                    for el in elements:
                        if el.is_displayed():
                            aria_dis = el.get_attribute("aria-disabled")
                            if aria_dis == "true":
                                continue
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                                time.sleep(0.3)
                                el.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", el)
                            return True
                except Exception:
                    pass
        time.sleep(1.5)
    return False



def simulate_random_human_activity(driver, stop_event=None):

    """
    Simulates highly natural, randomized human post-listing browsing.
    Stays 10-30 seconds total, picking randomly among Home feed, Reels, Watch, or Groups
    with variable scroll speeds, direction reversals, and natural pauses.
    """
    print("🎭 Starting post-listing randomized human simulation...")
    total_target_seconds = random.randint(12, 28)
    start_time = time.time()

    # 1. Brief initial pause on current page
    initial_pause = random.uniform(3.0, 6.0)
    time.sleep(initial_pause)

    modes = ["HOME_FEED", "REELS", "WATCH", "GROUPS"]
    mode = random.choice(modes)

    try:
        if mode == "HOME_FEED":
            print(f"🏠 [Simulation] Navigating to Home feed for {total_target_seconds}s...")
            driver.get("https://www.facebook.com")
            time.sleep(random.uniform(3.0, 5.0))

            while time.time() - start_time < total_target_seconds:
                if stop_event and stop_event.is_set():
                    break
                # Scroll down
                scroll_down_duration = random.randint(3, 6)
                scroll_end = time.time() + scroll_down_duration
                while time.time() < scroll_end:
                    try:
                        driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)
                    except Exception:
                        pass
                    time.sleep(random.uniform(1.2, 2.5))

                # Brief pause like reading a post
                time.sleep(random.uniform(2.0, 4.0))

                # Occasional scroll up
                if random.random() < 0.4:
                    try:
                        driver.find_element("tag name", "body").send_keys(Keys.PAGE_UP)
                    except Exception:
                        pass
                    time.sleep(random.uniform(1.5, 3.0))

        elif mode == "REELS":
            print(f"🎬 [Simulation] Navigating to Facebook Reels for {total_target_seconds}s...")
            driver.get("https://www.facebook.com/reels/")
            time.sleep(random.uniform(3.5, 6.0))

            while time.time() - start_time < total_target_seconds:
                if stop_event and stop_event.is_set():
                    break
                # Watch reel for 5-10 seconds
                watch_time = random.uniform(5.0, 10.0)
                sub_end = time.time() + watch_time
                while time.time() < sub_end:
                    if stop_event and stop_event.is_set():
                        break
                    time.sleep(0.5)
                # Next reel
                try:
                    driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)
                except Exception:
                    pass
                time.sleep(random.uniform(1.0, 2.0))

        elif mode == "WATCH":
            print(f"📺 [Simulation] Navigating to Facebook Watch videos for {total_target_seconds}s...")
            driver.get("https://www.facebook.com/watch")
            time.sleep(random.uniform(3.5, 5.5))

            while time.time() - start_time < total_target_seconds:
                if stop_event and stop_event.is_set():
                    break
                try:
                    driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)
                except Exception:
                    pass
                time.sleep(random.uniform(2.5, 5.0))

        else:  # GROUPS
            print(f"👥 [Simulation] Navigating to Facebook Groups feed for {total_target_seconds}s...")
            driver.get("https://www.facebook.com/groups/feed/")
            time.sleep(random.uniform(3.5, 5.5))

            while time.time() - start_time < total_target_seconds:
                if stop_event and stop_event.is_set():
                    break
                try:
                    driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)
                except Exception:
                    pass
                time.sleep(random.uniform(2.5, 4.5))

    except Exception as e:
        print(f"Note during simulation: {e}")

    print("✨ Post-listing human simulation complete.")


def check_account_health_and_previous_listing(driver):
    """
    Navigates to the Marketplace Selling dashboard to inspect:
    1. Account checkpoints / identity verification blocks.
    2. Marketplace bans / policy restrictions.
    3. Listing violations or removed listings.

    Returns (is_healthy: bool, flag_reason: str).
    If is_healthy is False, the caller will flag this ID and skip subsequent posts.
    """
    print("🔍 Inspecting account health and Marketplace Selling status...")
    flag_keywords = {
        "confirm your identity": "Identity Confirmation Checkpoint Triggered",
        "upload an id": "Upload ID Verification Required",
        "account restricted": "Account Restricted by Facebook",
        "your account has been disabled": "Account Disabled",
        "identity confirmation": "Identity Confirmation Required",
        "we've removed your listing": "Listing Removed for Policy Violation",
        "policy violation": "Policy Violation Detected",
        "listing violates": "Listing Violates Marketplace Commerce Policies",
        "has been flagged": "Listing / Account Flagged by Automated Review",
        "restricted from using marketplace": "Marketplace Access Restricted",
        "action required": "Action Required / Account Verification Needed",
        "request review": "Listing Rejected (Request Review Notice Visible)"
    }

    try:
        driver.get("https://www.facebook.com/marketplace/you/selling")
        time.sleep(random.uniform(5.0, 7.5))

        page_text = driver.execute_script("return document.body.innerText;").lower()

        for kw, reason in flag_keywords.items():
            if kw in page_text:
                print(f"🚨 CRITICAL ACCOUNT FLAG DETECTED: {reason}")
                return False, reason

        print("✅ Account health check passed. No restrictions or flags detected.")
        return True, ""

    except Exception as e:
        print(f"Warning during health check: {e}")
        return True, ""


def go_to_items(

    driver,
    title,
    price,
    category,
    condition,
    description,
    availability,
    product_tags,
    location,
    images,
    video,
    public_meetup,
    door_meetup,
    door_dropoff,
    marketplace_location="UK"
):
    print(f"📍 Location setting: {marketplace_location}")
    check_policy_keywords(title, description, price)
    try:


        seed=int(time.time())
        random.seed(seed)
        title_element = None
        time.sleep(random.randint(10, 15))
        done=False

        print("Scrolling")
        failed=True
        try:
            box = driver.find_element("xpath", "//div[@role='main'] | //div[contains(@aria-label, 'Marketplace')] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[2]" )
            outside_box = [box]
            failed=False
            print("Found outside box, single element")
        except Exception:
            pass
        if failed:

            scrollable_data = check_scrollable_elements(driver)
            print(scrollable_data)
            print("Found outside box")
            outside_box = []
            for item in scrollable_data:
                try:
                    el = driver.find_element("xpath", item['xpath'])
                    outside_box.append(el)
                except Exception:
                    pass
        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop += 500;", box)
            except Exception:
                pass
        time.sleep(random.randint(5,7))
        try:
            more_details_expand = driver.find_element("xpath", "//div[@role='button' and contains(normalize-space(.), 'More details')]")
            more_details_expand.click()
            time.sleep(random.randint(5,7))
        except Exception:
            print("More details button not present or already expanded")

        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop -= 500;", box)
            except Exception:
                pass    
        if marketplace_location=="UK":
            try:
                category_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Category')]//input | //input[contains(@aria-label, 'Category')]")
            except Exception:
                category_element = driver.find_element("xpath", "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/div[7]/div/div/div/div/div/div/div/label/div[1]/input")
            category_element.click()
            category_element.send_keys(category)
            time.sleep(random.randint(5,7))
            try:
                select_category_box = driver.find_element("xpath", "//ul[@role='listbox'] | //div[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/ul")
                category_list_items = select_category_box.find_elements("xpath", ".//li | .//div[@role='option']")
                if category_list_items:
                    category_list_items[0].click()
                    print("Clicked first category list item")
            except Exception as e:
                print(f"Category selection fallback: {e}")
 
        else:
            category_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Category') and @role='combobox']")
            category_element.click()
            time.sleep(random.randint(5,7))
            print("Looking for category options")
            xpath = f"//div[@role='button' and translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{category.lower()}']"
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(("xpath", xpath))
            )
            print(element, "Button to be selected")
            element.click()
        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop += 500;", box)
            except Exception:
                pass    
        try:
            description_label = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Description')]")
            description_element = description_label.find_element("xpath", ".//textarea")
            safe_paste(driver, description_element, description)
            time.sleep(random.randint(2,5))
            done=True
        except Exception as e:
            print(f"Description input error: {e}")
            pass
        try:
            availability_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Availability')]")
            availability_element.click()
            time.sleep(random.randint(2,5))
            outer_div = driver.find_element("xpath", "//div[@role='listbox'] | //ul[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/div/div/div/div[1]/div")
            inner_divs = outer_div.find_elements("xpath", ".//div | .//li")
            for div in inner_divs:
                lower_cases_availability=availability.lower()   
                lower_div_text=div.text.lower()  
                if lower_cases_availability in lower_div_text:
                    div.click()
                    print(f"Selected availability: {availability}")
                    break
        except Exception as e:
            print(f"Availability selection error: {e}")

        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop += 250;", box)
            except Exception:
                pass
        time.sleep(random.randint(5,7))
        print("Adding product tags")
        try:
            tags_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Product tags')]")
            text_area_tags = tags_element.find_element("tag name", "textarea")
            text_area_tags.click()
            text_area_tags.send_keys(", ".join(product_tags))
            text_area_tags.send_keys(Keys.ENTER)
            time.sleep(random.randint(5,7))
        except Exception as e:
            print(f"Tags input error: {e}")

        try:
            location_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Location')]")
            location_input = location_element.find_element("tag name", "input")
            location_input.click()
            location_input.clear()
            driver.execute_script("arguments[0].value = '';", location_input)
            location_input.send_keys(Keys.CONTROL + "a")
            location_input.send_keys(Keys.BACKSPACE)
            location_input.send_keys(location)
            location_input.click()
            time.sleep(random.randint(5,7))
            location_box = driver.find_element("xpath", "//ul[@role='listbox'] | //div[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/ul")
            list_items = location_box.find_elements("xpath", ".//li | .//div[@role='option']")
            if list_items:
                list_items[0].click()
                print("Clicked first list item")
                time.sleep(1)
        except Exception as e:
            print(f"Location input error: {e}")

        time.sleep(random.randint(5,7))
        if public_meetup==1:
            try:
                public_meetup_element = driver.find_element("xpath", "//div[contains(normalize-space(.), 'Public meetup') and @role='checkbox']")
                public_meetup_element.click()
                time.sleep(random.randint(5,7))
            except Exception:
                pass
        if door_meetup==1:
            try:
                door_meetup_element = driver.find_element("xpath", "//div[(contains(normalize-space(.), 'Door pickup') or contains(normalize-space(.), 'Door pick-up') or contains(normalize-space(.), 'Door pick')) and @role='checkbox']")
                door_meetup_element.click()
                time.sleep(random.randint(5,7))
            except Exception:
                pass
        if door_dropoff==1:
            try:
                door_dropoff_element = driver.find_element("xpath", "//div[(contains(normalize-space(.), 'Door dropoff') or contains(normalize-space(.), 'Door drop-off') or contains(normalize-space(.), 'Door drop')) and @role='checkbox']")
                door_dropoff_element.click()
                time.sleep(random.randint(5,7))
            except Exception:
                pass

        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop -= 500;", box)
            except Exception:
                pass    
        try:
            title_element = driver.find_element("xpath", "//input[contains(@placeholder,'Title')]")
        except Exception:
            pass
        if not title_element:
            try:
                title_element = driver.find_element("xpath", "//input[contains(@aria-label,'Title')]")
            except Exception:
                pass
        if not title_element:
            try:
                label = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Title')]")
                title_element = label.find_element("xpath", ".//input | .//textarea")
            except Exception:
                title_element = None
        if not title_element:
            title_element = driver.find_element("xpath", "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/label/div/input")
        
        safe_paste(driver, title_element, title)

        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop += 250;", box)
            except Exception:
                pass
        time.sleep(random.randint(5,7))
        price_element = None
        try:
            price_element = driver.find_element("xpath", "//input[contains(@placeholder,'Price')]")
        except Exception:
            pass
        if not price_element:
            try:
                price_element = driver.find_element("xpath", "//input[contains(@aria-label,'Price')]")
            except Exception:
                pass
        if not price_element:
            try:
                label = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Price')]")
                price_element = label.find_element("xpath", ".//input | .//textarea")
            except Exception:
                price_element = None
        if not price_element:
            price_element = driver.find_element("xpath", "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/div[6]/div/div/div/label/div/input")
        price_element.click()
        price_element.send_keys(price)
        time.sleep(random.randint(10,15))

        condition_element = None
        try:
            condition_element = driver.find_element("xpath", "//input[contains(@placeholder,'Condition')]")
        except Exception:
            pass
        if not condition_element:
            try:
                label = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Condition')]")
                try:
                    condition_element = label.find_element("xpath", ".//input")
                except Exception:
                    label.click()
                    time.sleep(random.randint(2,5))
                    condition_element = label
            except Exception:
                condition_element = None
        if not condition_element:
            condition_element = driver.find_element("xpath", "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/div[8]/div/div/div/div/label")
            condition_element.click()
        
        time.sleep(random.randint(10,15))
        try:
            popup_box = driver.find_element("xpath", "//div[@role='listbox'] | //ul[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/div/div/div/div[1]/div")
            divs = popup_box.find_elements("xpath", ".//div | .//li")

            # Normalize the target condition for comparison
            target = condition.lower().strip()
            target_dash = target.replace("-", "–")
            target_endash = target.replace("–", "-")

            # PASS 1: Exact match (prevents "New" from matching "Used - Like New")
            matched = False
            for div in divs:
                div_text = div.text.lower().strip()
                if div_text == target or div_text == target_dash or div_text == target_endash:
                    div.click()
                    print(f"Selected condition (exact): {condition}")
                    matched = True
                    break

            # PASS 2: Substring fallback only if exact match failed
            if not matched:
                for div in divs:
                    div_text = div.text.lower().strip()
                    if target in div_text or target_dash in div_text or target_endash in div_text:
                        div.click()
                        print(f"Selected condition (substring): {condition}")
                        matched = True
                        break

            if not matched:
                print(f"⚠️ Could not find condition '{condition}' in dropdown options.")
        except Exception as e:
            print(f"Condition selection popup error: {e}")

        time.sleep(random.randint(5,7))
        if not done:
            try:
                description_label = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Description')]")
                description_element = description_label.find_element("xpath", ".//textarea")
                safe_paste(driver, description_element, description)
                done=True
            except Exception:
                pass

        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop -= 500;", box)
            except Exception:
                pass
        time.sleep(random.randint(2,5))

        for image_path in images:
            try:
                # Anti-fingerprint photo before upload
                clean_img_path = anti_fingerprint_image(image_path)
                upload_input = driver.find_element("css selector", "input[type='file'][accept*='image']")
                driver.execute_script("arguments[0].value = '';", upload_input)
                upload_input.send_keys(clean_img_path)
            except Exception as e:
                print(f"Error uploading image {image_path}: {e}")
                return False

        if video and video.strip() != "":
            try:
                video_upload_input = driver.find_element("css selector", "input[type='file'][accept*='video']")
                video_upload_input.send_keys(video)
            except Exception as e:
                print(f"Error uploading video {video}: {e}")

        time.sleep(2)

        # Explicitly wait for image/video upload to complete before proceeding
        wait_for_media_upload(driver, max_wait=90)

        # 1. Click Next
        print("▶ Clicking 'Next' button...")
        next_success = find_and_click_button(driver, ["Next", "next"], timeout=60)
        if not next_success:
            print("⚠️ Could not find or click enabled 'Next' button after 60s timeout!")
            return False

        time.sleep(random.randint(6, 10))

        # 2. Click Publish
        print("📤 Clicking 'Publish' button...")
        publish_success = find_and_click_button(driver, ["Publish", "publish"], timeout=60)
        if not publish_success:
            print("⚠️ Could not find or click enabled 'Publish' button after 60s timeout!")
            return False

        # 3. Wait for Facebook to finish submitting the post (do NOT kill Chrome early!)
        print("⏳ Waiting for Facebook to complete listing publication...")
        pub_start = time.time()
        published_verified = False
        while time.time() - pub_start < 45:
            try:
                cur_url = driver.current_url.lower()
                # If page redirected away from /create/item, Facebook finished publishing!
                if "create/item" not in cur_url or "selling" in cur_url or "marketplace/item" in cur_url:
                    published_verified = True
                    print(f"✅ Verified: Listing published! Page redirected to {driver.current_url}")
                    break

                # Check for active listing confirmation banner
                dialogs = driver.find_elements("xpath", "//*[contains(text(), 'Your listing is active') or contains(text(), 'Listed') or contains(text(), 'Listing published')]")
                if any(d.is_displayed() for d in dialogs):
                    published_verified = True
                    print("✅ Verified: Active listing banner detected!")
                    break
            except Exception:
                pass
            time.sleep(2)

        if not published_verified:
            print("⌛ Finishing publication...")

        time.sleep(random.randint(8, 12))
        return True

    except Exception as e:
        print(f"Error during listing automation: {e}")
        time.sleep(random.randint(3, 5))
        return False