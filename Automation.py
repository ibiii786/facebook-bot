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








def human_scroll_to_element(driver, element):
    """Scroll smoothly to bring element into view, like a human using a mouse wheel."""
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element
        )
        time.sleep(random.uniform(0.4, 0.9))
    except Exception:
        pass


def human_click_fb_logo(driver):
    """Click the Facebook logo/home link instead of typing a URL."""
    for xp in [
        "//a[@aria-label='Facebook']",
        "//a[@title='Facebook']",
        "//a[contains(@href,'facebook.com') and .//*[name()='svg']]",
    ]:
        try:
            logo = driver.find_element("xpath", xp)
            if logo.is_displayed():
                human_scroll_to_element(driver, logo)
                time.sleep(random.uniform(0.5, 1.2))
                logo.click()
                return True
        except Exception:
            continue
    return False


def human_navigate_to(driver, url, link_hints=None):
    """Click a nav link by visible text; fall back to driver.get() if not found."""
    if link_hints:
        for hint in link_hints:
            try:
                el = driver.find_element(
                    "xpath",
                    f"//a[contains(normalize-space(.), '{hint}')] | "
                    f"//span[normalize-space(.)='{hint}']/ancestor::a"
                )
                if el.is_displayed():
                    human_scroll_to_element(driver, el)
                    time.sleep(random.uniform(0.5, 1.0))
                    el.click()
                    time.sleep(random.uniform(2.0, 4.0))
                    return True
            except Exception:
                continue
    driver.get(url)
    return False


def simulate_random_human_activity(driver, stop_event=None):



    """

    Simulates highly natural, randomized human post-listing browsing.

    Chains 2-4 random activities (Home feed, Reels, Watch, Groups, Marketplace browsing)

    for a total of 60-180 seconds with variable scroll speeds, direction reversals,

    and natural pauses between activities.

    """

    print("🎭 Starting post-listing randomized human simulation...")

    total_target_seconds = random.randint(60, 180)

    start_time = time.time()



    # 1. Brief initial pause on current page (like a human admiring their post)

    initial_pause = random.uniform(4.0, 10.0)

    time.sleep(initial_pause)



    # Pick 2-4 random activities to chain together

    all_modes = ["HOME_FEED", "REELS", "WATCH", "GROUPS", "MARKETPLACE_BROWSE"]

    num_activities = random.randint(2, 4)

    chosen_modes = random.sample(all_modes, min(num_activities, len(all_modes)))



    for mode_idx, mode in enumerate(chosen_modes):

        if time.time() - start_time >= total_target_seconds:

            break

        if stop_event and stop_event.is_set():

            break



        remaining_total = total_target_seconds - (time.time() - start_time)

        if remaining_total <= 5:

            break



        # Divide remaining time roughly among remaining activities

        remaining_activities = len(chosen_modes) - mode_idx

        activity_budget = remaining_total / remaining_activities

        # Add some randomness so each activity isn't the same length

        activity_duration = activity_budget * random.uniform(0.6, 1.4)

        activity_duration = max(15, min(activity_duration, remaining_total - 5))

        activity_end = time.time() + activity_duration



        try:

            if mode == "HOME_FEED":

                print(f"🏠 [Simulation] Browsing Home feed for ~{int(activity_duration)}s...")

                # Click Facebook logo like a human, not type URL

                if not human_click_fb_logo(driver):

                    driver.get("https://www.facebook.com")

                time.sleep(random.uniform(3.0, 6.0))



                while time.time() < activity_end:

                    if stop_event and stop_event.is_set():

                        break

                    # Scroll down a few times

                    scroll_count = random.randint(2, 5)

                    for _ in range(scroll_count):

                        if time.time() >= activity_end:

                            break

                        try:

                            driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)

                        except Exception:

                            pass

                        time.sleep(random.uniform(1.5, 3.5))



                    # Pause like reading a post

                    time.sleep(random.uniform(3.0, 8.0))



                    # Occasional scroll back up (like re-reading something)

                    if random.random() < 0.35:

                        scroll_up_count = random.randint(1, 3)

                        for _ in range(scroll_up_count):

                            try:

                                driver.find_element("tag name", "body").send_keys(Keys.PAGE_UP)

                            except Exception:

                                pass

                            time.sleep(random.uniform(1.0, 2.5))

                        time.sleep(random.uniform(2.0, 5.0))



            elif mode == "REELS":

                print(f"🎬 [Simulation] Watching Reels for ~{int(activity_duration)}s...")

                # Click Reels nav link like a human

                if not human_navigate_to(driver, "https://www.facebook.com/reels/", ["Reels"]):

                    pass  # already navigated by click

                time.sleep(random.uniform(4.0, 7.0))



                while time.time() < activity_end:

                    if stop_event and stop_event.is_set():

                        break

                    # Watch a reel for 8-20 seconds

                    watch_time = random.uniform(8.0, 20.0)

                    sub_end = min(time.time() + watch_time, activity_end)

                    while time.time() < sub_end:

                        if stop_event and stop_event.is_set():

                            break

                        time.sleep(0.5)

                    # Swipe to next reel

                    try:

                        driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)

                    except Exception:

                        pass

                    time.sleep(random.uniform(1.0, 3.0))



            elif mode == "WATCH":

                print(f"📺 [Simulation] Browsing Facebook Watch for ~{int(activity_duration)}s...")

                # Click Watch nav link like a human

                if not human_navigate_to(driver, "https://www.facebook.com/watch", ["Watch"]):

                    pass

                time.sleep(random.uniform(4.0, 6.0))



                while time.time() < activity_end:

                    if stop_event and stop_event.is_set():

                        break

                    # Watch for a bit then scroll

                    time.sleep(random.uniform(5.0, 12.0))

                    try:

                        driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)

                    except Exception:

                        pass

                    time.sleep(random.uniform(2.0, 4.0))



            elif mode == "GROUPS":

                print(f"👥 [Simulation] Browsing Groups feed for ~{int(activity_duration)}s...")

                # Click Groups nav link like a human

                if not human_navigate_to(driver, "https://www.facebook.com/groups/feed/", ["Groups"]):

                    pass

                time.sleep(random.uniform(4.0, 6.0))



                while time.time() < activity_end:

                    if stop_event and stop_event.is_set():

                        break

                    scroll_count = random.randint(1, 3)

                    for _ in range(scroll_count):

                        if time.time() >= activity_end:

                            break

                        try:

                            driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)

                        except Exception:

                            pass

                        time.sleep(random.uniform(2.0, 4.0))

                    time.sleep(random.uniform(3.0, 7.0))



            elif mode == "MARKETPLACE_BROWSE":

                print(f"🛒 [Simulation] Browsing Marketplace for ~{int(activity_duration)}s...")

                # Click Marketplace nav link like a human

                if not human_navigate_to(driver, "https://www.facebook.com/marketplace/", ["Marketplace"]):

                    pass

                time.sleep(random.uniform(4.0, 7.0))



                while time.time() < activity_end:

                    if stop_event and stop_event.is_set():

                        break

                    scroll_count = random.randint(2, 4)

                    for _ in range(scroll_count):

                        if time.time() >= activity_end:

                            break

                        try:

                            driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)

                        except Exception:

                            pass

                        time.sleep(random.uniform(1.5, 3.5))

                    time.sleep(random.uniform(3.0, 6.0))



        except Exception as e:

            print(f"Note during simulation ({mode}): {e}")



        # Brief transition pause between activities (like a human deciding what to do next)

        if mode_idx < len(chosen_modes) - 1 and time.time() - start_time < total_target_seconds:

            transition_pause = random.uniform(2.0, 5.0)

            time.sleep(transition_pause)



    elapsed = int(time.time() - start_time)

    print(f"✨ Post-listing human simulation complete ({elapsed}s across {len(chosen_modes)} activities).")





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

        # Navigate to Selling dashboard via Marketplace link, human-style

        if not human_navigate_to(driver, "https://www.facebook.com/marketplace/you/selling", ["Your listings", "Selling", "Your account"]):

            pass  # already loaded by click or fallback

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

        # ── Find the scrollable form container ──────────────────────────────
        outside_box = []
        try:
            box = driver.find_element("xpath", "//div[@role='main'] | //div[contains(@aria-label, 'Marketplace')] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[2]")
            outside_box = [box]
        except Exception:
            scrollable_data = check_scrollable_elements(driver)
            for item in scrollable_data:
                try:
                    el = driver.find_element("xpath", item['xpath'])
                    outside_box.append(el)
                except Exception:
                    pass

        def scroll_form_to(px, direction=1):
            """Smooth-scroll the form container by px amount in steps, like a human."""
            steps = max(1, abs(px) // 60)
            step_px = (px // steps) * direction
            for _ in range(steps):
                for box in outside_box:
                    try:
                        driver.execute_script("arguments[0].scrollTop += arguments[1];", box, step_px)
                    except Exception:
                        try:
                            driver.execute_script("window.scrollBy(0, arguments[0]);", step_px)
                        except Exception:
                            pass
                time.sleep(random.uniform(0.04, 0.09))

        def scroll_to_field(element):
            """Human-like scroll to bring a specific field into comfortable view."""
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    element
                )
                time.sleep(random.uniform(0.4, 0.9))
            except Exception:
                scroll_form_to(200)

        # ── Expand More Details if present (do this early, at top of form) ──
        try:
            more_details_expand = driver.find_element("xpath", "//div[@role='button' and contains(normalize-space(.), 'More details')]")
            scroll_to_field(more_details_expand)
            more_details_expand.click()
            time.sleep(random.randint(2, 4))
        except Exception:
            pass

        # ── Scroll back to TOP of form before filling fields ────────────────
        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop = 0;", box)
            except Exception:
                pass
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(1.0, 2.0))

        # ══════════════════════════════════════════════════════════════════════
        # FILL FIELDS TOP-TO-BOTTOM (like a human reading the form from top)
        # Order: Title -> Price -> Category -> Condition -> Description ->
        #        Availability -> Tags -> Location -> Delivery checkboxes
        # ══════════════════════════════════════════════════════════════════════

        # 1. TITLE (topmost field on the form)
        print("Filling Title...")
        title_element = None
        for xp in [
            "//input[contains(@placeholder,'Title')]",
            "//input[contains(@aria-label,'Title')]",
            "//label[contains(normalize-space(.), 'Title')]//input",
            "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/label/div/input",
        ]:
            try:
                title_element = driver.find_element("xpath", xp)
                if title_element.is_displayed():
                    break
            except Exception:
                title_element = None
        if title_element:
            scroll_to_field(title_element)
            time.sleep(random.uniform(0.5, 1.0))
            safe_paste(driver, title_element, title)
            time.sleep(random.uniform(1.5, 3.0))

        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 2. PRICE
        print("Filling Price...")
        price_element = None
        for xp in [
            "//input[contains(@placeholder,'Price')]",
            "//input[contains(@aria-label,'Price')]",
            "//label[contains(normalize-space(.), 'Price')]//input",
            "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/div[6]/div/div/div/label/div/input",
        ]:
            try:
                price_element = driver.find_element("xpath", xp)
                if price_element.is_displayed():
                    break
            except Exception:
                price_element = None
        if price_element:
            scroll_to_field(price_element)
            time.sleep(random.uniform(0.5, 1.0))
            price_element.click()
            time.sleep(random.uniform(0.3, 0.6))
            price_element.send_keys(price)
            time.sleep(random.uniform(1.5, 3.0))

        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 3. CATEGORY
        print("Filling Category...")
        if marketplace_location == "UK":
            try:
                category_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Category')]//input | //input[contains(@aria-label, 'Category')]")
            except Exception:
                category_element = driver.find_element("xpath", "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/div[7]/div/div/div/div/div/div/div/label/div[1]/input")
            scroll_to_field(category_element)
            time.sleep(random.uniform(0.4, 0.8))
            category_element.click()
            category_element.send_keys(category)
            time.sleep(random.randint(4, 6))
            try:
                select_category_box = driver.find_element("xpath", "//ul[@role='listbox'] | //div[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/ul")
                category_list_items = select_category_box.find_elements("xpath", ".//li | .//div[@role='option']")
                if category_list_items:
                    category_list_items[0].click()
            except Exception as e:
                print(f"Category selection fallback: {e}")
        else:
            category_element = None
            for xp in [
                "//label[contains(normalize-space(.), 'Category')]//input",
                "//input[contains(@aria-label, 'Category')]",
                "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/div[7]/div/div/div/div/div/div/div/label/div[1]/input",
            ]:
                try:
                    category_element = driver.find_element("xpath", xp)
                    break
                except Exception:
                    continue
            if category_element is None:
                raise Exception("Could not locate Category input field.")
            scroll_to_field(category_element)
            time.sleep(random.uniform(0.4, 0.8))
            category_element.click()
            category_element.send_keys(category)
            time.sleep(random.randint(4, 7))
            selected = False
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                xpath_btn = f"//div[@role='button' and translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '{category.lower()}']"
                element = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(("xpath", xpath_btn)))
                element.click()
                selected = True
            except Exception:
                pass
            if not selected:
                try:
                    select_category_box = driver.find_element("xpath", "//ul[@role='listbox'] | //div[@role='listbox']")
                    items = select_category_box.find_elements("xpath", ".//li | .//div[@role='option']")
                    if items:
                        items[0].click()
                except Exception as e:
                    print(f"Category listbox fallback failed: {e}")

        time.sleep(random.uniform(1.5, 3.0))
        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 4. CONDITION
        print("Selecting Condition...")
        condition_element = None
        for xp in [
            "//input[contains(@placeholder,'Condition')]",
            "//label[contains(normalize-space(.), 'Condition')]//input",
        ]:
            try:
                condition_element = driver.find_element("xpath", xp)
                if condition_element.is_displayed():
                    break
            except Exception:
                condition_element = None
        if not condition_element:
            try:
                label = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Condition')]")
                scroll_to_field(label)
                label.click()
                time.sleep(random.randint(2, 4))
                condition_element = label
            except Exception:
                try:
                    condition_element = driver.find_element("xpath", "/html/body/div[1]/div/div[1]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/div[8]/div/div/div/div/label")
                    scroll_to_field(condition_element)
                    condition_element.click()
                except Exception:
                    pass
        if condition_element and hasattr(condition_element, 'is_displayed') and condition_element.is_displayed():
            scroll_to_field(condition_element)
            time.sleep(random.uniform(0.4, 0.8))
            try:
                condition_element.click()
            except Exception:
                pass
        time.sleep(random.randint(2, 4))
        try:
            popup_box = driver.find_element("xpath", "//div[@role='listbox'] | //ul[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/div/div/div/div[1]/div")
            divs = popup_box.find_elements("xpath", ".//div | .//li")
            target = condition.lower().strip()
            matched = False
            for div in divs:
                div_text = div.text.lower().strip()
                if div_text == target or div_text == target.replace("-", "\u2013") or div_text == target.replace("\u2013", "-"):
                    div.click()
                    matched = True
                    break
            if not matched:
                for div in divs:
                    div_text = div.text.lower().strip()
                    if target in div_text:
                        div.click()
                        matched = True
                        break
            if not matched:
                print(f"Could not find condition '{condition}' in dropdown.")
        except Exception as e:
            print(f"Condition popup error: {e}")

        time.sleep(random.uniform(1.5, 3.0))
        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 5. DESCRIPTION
        print("Filling Description...")
        try:
            description_label = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Description')]")
            description_element = description_label.find_element("xpath", ".//textarea")
            scroll_to_field(description_element)
            time.sleep(random.uniform(0.4, 0.8))
            safe_paste(driver, description_element, description)
            time.sleep(random.uniform(2.0, 4.0))
        except Exception as e:
            print(f"Description input error: {e}")

        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 6. AVAILABILITY
        print("Selecting Availability...")
        try:
            availability_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Availability')]")
            scroll_to_field(availability_element)
            time.sleep(random.uniform(0.4, 0.8))
            availability_element.click()
            time.sleep(random.randint(2, 4))
            outer_div = driver.find_element("xpath", "//div[@role='listbox'] | //ul[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/div/div/div/div[1]/div")
            inner_divs = outer_div.find_elements("xpath", ".//div | .//li")
            for div in inner_divs:
                if availability.lower() in div.text.lower():
                    div.click()
                    break
        except Exception as e:
            print(f"Availability selection error: {e}")

        time.sleep(random.uniform(1.5, 3.0))
        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 7. PRODUCT TAGS
        print("Adding Product Tags...")
        try:
            tags_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Product tags')]")
            text_area_tags = tags_element.find_element("tag name", "textarea")
            scroll_to_field(text_area_tags)
            time.sleep(random.uniform(0.4, 0.8))
            text_area_tags.click()
            time.sleep(random.uniform(0.3, 0.6))
            text_area_tags.send_keys(", ".join(product_tags))
            text_area_tags.send_keys(Keys.ENTER)
            time.sleep(random.randint(3, 6))
        except Exception as e:
            print(f"Tags input error: {e}")

        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 8. LOCATION
        print("Filling Location...")
        try:
            location_element = driver.find_element("xpath", "//label[contains(normalize-space(.), 'Location')]")
            location_input = location_element.find_element("tag name", "input")
            scroll_to_field(location_input)
            time.sleep(random.uniform(0.4, 0.8))
            location_input.click()
            location_input.clear()
            driver.execute_script("arguments[0].value = '';", location_input)
            location_input.send_keys(Keys.CONTROL + "a")
            location_input.send_keys(Keys.BACKSPACE)
            location_input.send_keys(location)
            time.sleep(random.randint(4, 6))
            location_box = driver.find_element("xpath", "//ul[@role='listbox'] | //div[@role='listbox'] | /html/body/div[1]/div/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/div[1]/div/ul")
            list_items = location_box.find_elements("xpath", ".//li | .//div[@role='option']")
            if list_items:
                list_items[0].click()
                time.sleep(1)
        except Exception as e:
            print(f"Location input error: {e}")

        scroll_form_to(200)
        time.sleep(random.uniform(0.5, 1.0))

        # 9. DELIVERY CHECKBOXES
        if public_meetup == 1:
            try:
                el = driver.find_element("xpath", "//div[contains(normalize-space(.), 'Public meetup') and @role='checkbox']")
                scroll_to_field(el)
                time.sleep(random.uniform(0.3, 0.7))
                el.click()
                time.sleep(random.randint(2, 4))
            except Exception:
                pass
        if door_meetup == 1:
            try:
                el = driver.find_element("xpath", "//div[(contains(normalize-space(.), 'Door pickup') or contains(normalize-space(.), 'Door pick-up')) and @role='checkbox']")
                scroll_to_field(el)
                time.sleep(random.uniform(0.3, 0.7))
                el.click()
                time.sleep(random.randint(2, 4))
            except Exception:
                pass
        if door_dropoff == 1:
            try:
                el = driver.find_element("xpath", "//div[(contains(normalize-space(.), 'Door dropoff') or contains(normalize-space(.), 'Door drop-off')) and @role='checkbox']")
                scroll_to_field(el)
                time.sleep(random.uniform(0.3, 0.7))
                el.click()
                time.sleep(random.randint(2, 4))
            except Exception:
                pass

        # Scroll back to top before image upload section
        for box in outside_box:
            try:
                driver.execute_script("arguments[0].scrollTop = 0;", box)
            except Exception:
                pass
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(1.0, 2.0))

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



        # Multi-window wizard loop (handles standard 2-window and alternate 3-window / split flows)

        wizard_step = 1

        max_wizard_steps = 6



        while wizard_step <= max_wizard_steps:

            print(f"📋 [Wizard Step {wizard_step}] Inspecting screen and navigation buttons...")

            time.sleep(random.randint(4, 6))



            # Fill any form fields that appear on this step (handles Facebook split layouts)

            try:

                # 1. Title if empty

                try:

                    t_inputs = driver.find_elements("xpath", "//input[contains(@placeholder,'Title') or contains(@aria-label,'Title')] | //label[contains(normalize-space(.), 'Title')]//input")

                    for inp in t_inputs:

                        if inp.is_displayed():

                            cur = inp.get_attribute("value") or ""

                            if not cur.strip() and title:

                                print(f"Filling Title on step {wizard_step}...")

                                safe_paste(driver, inp, title)

                except Exception:

                    pass



                # 2. Price if empty

                try:

                    p_inputs = driver.find_elements("xpath", "//input[contains(@placeholder,'Price') or contains(@aria-label,'Price')] | //label[contains(normalize-space(.), 'Price')]//input")

                    for inp in p_inputs:

                        if inp.is_displayed():

                            cur = inp.get_attribute("value") or ""

                            if not cur.strip() and price:

                                print(f"Filling Price on step {wizard_step}...")

                                inp.click()

                                inp.send_keys(Keys.CONTROL + 'a')

                                inp.send_keys(Keys.BACKSPACE)

                                inp.send_keys(str(price))

                except Exception:

                    pass



                # 3. Category if empty

                try:

                    cat_inputs = driver.find_elements("xpath", "//label[contains(normalize-space(.), 'Category')]//input | //input[contains(@aria-label, 'Category')]")

                    for inp in cat_inputs:

                        if inp.is_displayed():

                            cur = inp.get_attribute("value") or ""

                            if not cur.strip() and category:

                                print(f"Filling Category on step {wizard_step}...")

                                inp.click()

                                inp.send_keys(category)

                                time.sleep(random.randint(3, 5))

                                suggs = driver.find_elements("xpath", "//ul[@role='listbox']//li | //div[@role='listbox']//div[@role='option']")

                                if suggs:

                                    suggs[0].click()

                except Exception:

                    pass



                # 4. Condition if empty

                try:

                    c_inputs = driver.find_elements("xpath", "//label[contains(normalize-space(.), 'Condition')]")

                    for inp in c_inputs:

                        if inp.is_displayed():

                            cur = inp.text or inp.get_attribute("value") or ""

                            if condition.lower() not in cur.lower() and condition:

                                print(f"Selecting Condition on step {wizard_step}...")

                                inp.click()

                                time.sleep(random.randint(2, 4))

                                opts = driver.find_elements("xpath", "//div[@role='listbox']//div | //ul[@role='listbox']//li")

                                target = condition.lower().strip()

                                for opt in opts:

                                    if target in opt.text.lower():

                                        opt.click()

                                        break

                except Exception:

                    pass



                # 5. Description if empty

                try:

                    d_inputs = driver.find_elements("xpath", "//label[contains(normalize-space(.), 'Description')]//textarea | //textarea[contains(@placeholder, 'Description') or contains(@aria-label, 'Description')]")

                    for inp in d_inputs:

                        if inp.is_displayed():

                            cur = inp.get_attribute("value") or ""

                            if not cur.strip() and description:

                                print(f"Filling Description on step {wizard_step}...")

                                safe_paste(driver, inp, description)

                except Exception:

                    pass



                # 6. Availability if empty

                try:

                    a_inputs = driver.find_elements("xpath", "//label[contains(normalize-space(.), 'Availability')]")

                    for inp in a_inputs:

                        if inp.is_displayed():

                            cur = inp.text or inp.get_attribute("value") or ""

                            if availability.lower() not in cur.lower() and availability:

                                print(f"Selecting Availability on step {wizard_step}...")

                                inp.click()

                                time.sleep(random.randint(2, 3))

                                opts = driver.find_elements("xpath", "//div[@role='listbox']//div | //ul[@role='listbox']//li")

                                for opt in opts:

                                    if availability.lower() in opt.text.lower():

                                        opt.click()

                                        break

                except Exception:

                    pass



                # 7. Product tags if empty

                try:

                    tag_inputs = driver.find_elements("xpath", "//label[contains(normalize-space(.), 'Product tags')]//textarea | //textarea[contains(@aria-label, 'Product tags')]")

                    for inp in tag_inputs:

                        if inp.is_displayed():

                            cur = inp.get_attribute("value") or ""

                            if not cur.strip() and product_tags:

                                print(f"Filling Product Tags on step {wizard_step}...")

                                inp.click()

                                inp.send_keys(", ".join(product_tags))

                                inp.send_keys(Keys.ENTER)

                except Exception:

                    pass



                # 8. Location if empty

                try:

                    loc_inputs = driver.find_elements("xpath", "//label[contains(normalize-space(.), 'Location')]//input | //input[contains(@aria-label, 'Location') or contains(@placeholder, 'Location')]")

                    for inp in loc_inputs:

                        if inp.is_displayed():

                            cur = inp.get_attribute("value") or ""

                            if not cur.strip() and location:

                                print(f"Filling Location on step {wizard_step}...")

                                inp.click()

                                inp.clear()

                                inp.send_keys(Keys.CONTROL + 'a')

                                inp.send_keys(Keys.BACKSPACE)

                                inp.send_keys(location)

                                time.sleep(random.randint(3, 5))

                                suggs = driver.find_elements("xpath", "//ul[@role='listbox']//li | //div[@role='listbox']//div[@role='option']")

                                if suggs:

                                    suggs[0].click()

                except Exception:

                    pass



            except Exception as e:

                print(f"Notice while verifying fields on step {wizard_step}: {e}")



            time.sleep(2)



            # Scroll down to ensure navigation button is in view

            for box in outside_box:

                try:

                    driver.execute_script("arguments[0].scrollTop += 800;", box)

                except Exception:

                    pass

            time.sleep(random.randint(2, 4))



            # Check if Publish button is present and enabled

            publish_btns = driver.find_elements("xpath", "//div[@role='button' and (normalize-space(.)='Publish' or normalize-space(.)='publish' or contains(@aria-label, 'Publish'))] | //button[normalize-space(.)='Publish' or contains(@aria-label, 'Publish')]")

            publish_clickable = None

            for pb in publish_btns:

                if pb.is_displayed():

                    aria_dis = pb.get_attribute("aria-disabled")

                    if aria_dis != "true" and pb.get_attribute("disabled") is None:

                        publish_clickable = pb

                        break



            if publish_clickable:

                print(f"📤 [Step {wizard_step}] Found enabled 'Publish' button! Clicking to publish...")

                try:

                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", publish_clickable)

                    time.sleep(0.3)

                    publish_clickable.click()

                except Exception:

                    driver.execute_script("arguments[0].click();", publish_clickable)

                break



            # If no Publish button or Publish is disabled, check for Next button

            next_btns = driver.find_elements("xpath", "//div[@role='button' and (normalize-space(.)='Next' or normalize-space(.)='next' or contains(@aria-label, 'Next'))] | //button[normalize-space(.)='Next' or contains(@aria-label, 'Next')]")

            next_clickable = None

            for nb in next_btns:

                if nb.is_displayed():

                    aria_dis = nb.get_attribute("aria-disabled")

                    if aria_dis != "true" and nb.get_attribute("disabled") is None:

                        next_clickable = nb

                        break



            if next_clickable:

                print(f"▶ [Step {wizard_step}] Found enabled 'Next' button! Clicking to move to next window...")

                try:

                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_clickable)

                    time.sleep(0.3)

                    next_clickable.click()

                except Exception:

                    driver.execute_script("arguments[0].click();", next_clickable)



                wizard_step += 1

                time.sleep(random.randint(4, 7))

                continue



            # If neither an enabled Publish nor enabled Next button was found, wait briefly and retry checking

            print(f"⏳ [Step {wizard_step}] Neither Next nor Publish enabled yet - waiting 5s before retrying same step...")

            time.sleep(5)

            # NOTE: do NOT increment wizard_step here - we retry the same step until a button appears



        if wizard_step > max_wizard_steps and not publish_clickable:

            print("⚠️ Wizard did not find enabled Publish button after all steps.")

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