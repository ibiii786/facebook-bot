import os
import sys
import json
import time
import random
import threading
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from Automation import (
    go_to_items,
    simulate_random_human_activity,
    check_account_health_and_previous_listing
)

from login_profile import email_to_safe
from path import move_to_path
from save_state import make_files, set_file_status

CSV_PATH = "emails.csv"
saved_states_file = "saved_states.csv"
FLAGGED_ACCOUNTS_FILE = "flagged_accounts.json"
IMAGE_USAGE_LOG_FILE = "image_usage_log.json"

_flag_lock = threading.Lock()
_image_usage_lock = threading.Lock()


def load_image_usage_log() -> Dict[str, list]:
    """Load the per-account image usage log. Returns {image_path: [email1, email2, ...]}"""
    with _image_usage_lock:
        if not os.path.exists(IMAGE_USAGE_LOG_FILE):
            return {}
        try:
            with open(IMAGE_USAGE_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}


def record_image_usage(images: List[str], email: str):
    """Record that these images were used on this account after a successful listing."""
    with _image_usage_lock:
        data = {}
        if os.path.exists(IMAGE_USAGE_LOG_FILE):
            try:
                with open(IMAGE_USAGE_LOG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        for img in images:
            img = img.strip()
            if not img:
                continue
            if img not in data:
                data[img] = []
            if email not in data[img]:
                data[img].append(email)
        try:
            with open(IMAGE_USAGE_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving image usage log: {e}")


def check_image_usage(images: List[str], email: str) -> List[str]:
    """
    Check if any images have already been used on this account.
    Returns a list of warning strings for any duplicates detected.
    """
    usage = load_image_usage_log()
    warnings = []
    for img in images:
        img = img.strip()
        if not img:
            continue
        used_by = usage.get(img, [])
        if email in used_by:
            warnings.append(f"⚠️ Image already used on this account: {os.path.basename(img)}")
        elif used_by:
            other_accounts = [e for e in used_by if e != email]
            if other_accounts:
                # Used on OTHER accounts but not this one — OK, just informational
                pass
    return warnings



def load_flagged_accounts() -> Dict[str, dict]:
    with _flag_lock:
        if not os.path.exists(FLAGGED_ACCOUNTS_FILE):
            return {}
        try:
            with open(FLAGGED_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

def flag_account(email: str, reason: str, listing_title: str = ""):
    with _flag_lock:
        data = {}
        if os.path.exists(FLAGGED_ACCOUNTS_FILE):
            try:
                with open(FLAGGED_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[email] = {
            "email": email,
            "reason": reason,
            "listing_title": listing_title,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            with open(FLAGGED_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving flagged accounts: {e}")

def unflag_account(email: str):
    with _flag_lock:
        if not os.path.exists(FLAGGED_ACCOUNTS_FILE):
            return
        try:
            with open(FLAGGED_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if email in data:
                del data[email]
                with open(FLAGGED_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error unflagging account: {e}")



# ── Global Thread-Safe Live Status Tracker & Active Driver Registry ───────
_status_lock = threading.Lock()
LIVE_BOT_STATE: Dict[str, Any] = {
    "status": "idle",  # idle | running | stopping
    "active_browsers": 0,
    "max_concurrent": 2,
    "completed_listings": 0,
    "total_listings": 0,
    "accounts": {},
    "logs": [],
    "failed": {}
}

active_drivers_lock = threading.Lock()
ACTIVE_DRIVERS: List[webdriver.Chrome] = []


def stop_all_active_drivers():
    """Immediately terminates all open Chrome browser instances launched by the orchestrator."""
    with active_drivers_lock:
        log_live_message(f"⏹ Force stopping {len(ACTIVE_DRIVERS)} active Chrome instances...")
        for driver in list(ACTIVE_DRIVERS):
            try:
                driver.quit()
            except Exception:
                pass
        ACTIVE_DRIVERS.clear()


def get_live_bot_state() -> Dict[str, Any]:
    with _status_lock:
        return json_safe_copy(LIVE_BOT_STATE)


def json_safe_copy(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: json_safe_copy(v) for k, v in data.items()}
    if isinstance(data, list):
        return [json_safe_copy(v) for v in data]
    return data



def log_live_message(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with _status_lock:
        LIVE_BOT_STATE["logs"].append(formatted)
        if len(LIVE_BOT_STATE["logs"]) > 100:
            LIVE_BOT_STATE["logs"].pop(0)


def update_account_state(email: str, state: str, details: str = "", stage: str = "", elapsed_mins: float = 0.0, cooldown_remaining: int = 0, fb_name: str = ""):
    with _status_lock:
        from account_names import get_account_fb_name
        resolved_name = fb_name or get_account_fb_name(email)
        if email not in LIVE_BOT_STATE["accounts"]:
            LIVE_BOT_STATE["accounts"][email] = {
                "email": email,
                "fb_name": resolved_name,
                "state": state,
                "details": details,
                "stage": stage,
                "elapsed_mins": elapsed_mins,
                "cooldown_remaining": cooldown_remaining,
                "active_listing": "",
                "browser_open": False
            }
        else:
            acc = LIVE_BOT_STATE["accounts"][email]
            acc["state"] = state
            acc["details"] = details
            if resolved_name:
                acc["fb_name"] = resolved_name
            if stage:
                acc["stage"] = stage
            if elapsed_mins is not None:
                acc["elapsed_mins"] = elapsed_mins
            if cooldown_remaining is not None:
                acc["cooldown_remaining"] = cooldown_remaining


def read_multiple_credentials(path: str = CSV_PATH) -> List[tuple]:
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
            if email or phone:
                creds.append((email, phone, proxy))
    except Exception as e:
        print(f"Error reading credentials CSV: {e}")
    return creds


def _interruptible_sleep(seconds: float, stop_event: Optional[threading.Event], email: Optional[str] = None, state_label: str = "Cooldown") -> bool:
    """Sleep in 0.5s increments with real-time cooldown countdown updates."""
    if stop_event is None:
        time.sleep(seconds)
        return True

    end = time.time() + seconds
    while time.time() < end:
        if stop_event.is_set():
            return False
        remaining = int(end - time.time())
        if email and remaining % 5 == 0:
            mins, secs = divmod(remaining, 60)
            update_account_state(
                email=email,
                state="COOLDOWN",
                details=f"{state_label}: {mins}m {secs}s remaining",
                cooldown_remaining=remaining
            )
        time.sleep(0.5)

    if email:
        update_account_state(email=email, state="READY", details="Ready for next task", cooldown_remaining=0)
    return True


_global_post_lock = threading.Lock()
_global_last_post_time: float = 0.0


# ── Account Worker Lifecycle Engine ─────────────────────────────────────────
class AccountLifecycleWorker(threading.Thread):
    def __init__(
        self,
        account_tuple: tuple,
        assigned_entries: list,
        location_list: list,
        marketplace_location: str = "UK",
        time_sleep_cooldown: int = 1800,
        wait_time_accounts: int = 2,
        wait_for_review: bool = False,
        stop_event: Optional[threading.Event] = None,
        semaphore: Optional[threading.Semaphore] = None,
        max_review_timeout: int = 1800
    ):
        super().__init__(daemon=True)
        self.email = account_tuple[0]
        self.phone = account_tuple[1] if len(account_tuple) > 1 else ""
        self.proxy = account_tuple[2] if len(account_tuple) > 2 else ""
        self.assigned_entries = assigned_entries
        self.location_list = location_list
        self.marketplace_location = marketplace_location
        self.time_sleep_cooldown = time_sleep_cooldown
        self.wait_time_accounts = wait_time_accounts
        self.wait_for_review = wait_for_review
        self.stop_event = stop_event or threading.Event()
        self.semaphore = semaphore
        self.max_review_timeout = max_review_timeout
        self.failed_listings = []
        from account_names import get_account_fb_name
        self.fb_name = get_account_fb_name(self.email or self.phone)

    def run(self):
        global _global_last_post_time
        email = self.email
        display_id = self.fb_name or email


        # ── 0. Check if Account is Already Flagged ──
        flagged_map = load_flagged_accounts()
        if email in flagged_map:
            info = flagged_map[email]
            reason = info.get("reason", "Account flagged")
            log_live_message(f"⚠️ [{email}] Account is FLAGGED ({reason}). Skipping all tasks for this account.")
            update_account_state(email, state="FLAGGED", details=f"Skipped: {reason}")
            return

        log_live_message(f"🚀 Worker started for account: {email} ({len(self.assigned_entries)} listings assigned)")
        update_account_state(email, state="QUEUED", details=f"Queued ({len(self.assigned_entries)} listings)")

        for idx, entry in enumerate(self.assigned_entries):
            if self.stop_event.is_set():
                log_live_message(f"🛑 Worker stopped for {email}")
                update_account_state(email, state="STOPPED", details="Halted by user")
                return

            loc = self.location_list[idx % len(self.location_list)] if self.location_list else ""
            title = entry[1].get() if len(entry) > 1 else f"Listing #{idx+1}"

            # ── 1. Enforce Global Inter-Account Stagger Delay ──
            if self.wait_time_accounts > 0:
                with _global_post_lock:
                    now = time.time()
                    elapsed = now - _global_last_post_time
                    if _global_last_post_time > 0 and elapsed < self.wait_time_accounts:
                        stagger_wait = self.wait_time_accounts - elapsed
                        log_live_message(f"⏳ [{email}] Waiting {int(stagger_wait)}s inter-account stagger delay to protect account...")
                        update_account_state(email, state="COOLDOWN", details=f"Inter-Account Delay: {int(stagger_wait)}s remaining")
                        if not _interruptible_sleep(stagger_wait, self.stop_event, email=email, state_label="Inter-Account Stagger Delay"):
                            return
                    _global_last_post_time = time.time()

            # ── 2. Acquire concurrency slot ──
            update_account_state(email, state="WAITING_SLOT", details=f"Waiting for available browser slot to post '{title}'")
            if self.semaphore:
                acquired = False
                while not acquired:
                    if self.stop_event.is_set():
                        return
                    acquired = self.semaphore.acquire(timeout=1.0)

            with _status_lock:
                LIVE_BOT_STATE["active_browsers"] += 1
                if email in LIVE_BOT_STATE["accounts"]:
                    LIVE_BOT_STATE["accounts"][email]["browser_open"] = True

            MAX_RETRIES = 3
            listing_succeeded = False

            for attempt in range(1, MAX_RETRIES + 1):
                if self.stop_event.is_set():
                    break

                driver = None
                keep_browser_open = False
                try:
                    if attempt > 1:
                        log_live_message(f"🔄 [{email}] Retry {attempt}/{MAX_RETRIES} for listing '{title}'...")
                        update_account_state(email, state="LAUNCHING", details=f"Retry {attempt}/{MAX_RETRIES} for '{title}'")
                    else:
                        log_live_message(f"🌐 [{email}] Launching Chrome profile for listing '{title}'...")
                        update_account_state(email, state="LAUNCHING", details=f"Starting Chrome for '{title}'")

                    safe_email = email_to_safe(email, self.phone)
                    base_profile_dir = Path("profiles")
                    profile_dir = base_profile_dir / safe_email
                    profile_dir.mkdir(parents=True, exist_ok=True)

                    # Clean up any leftover browser singleton locks
                    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]:
                        lock_file = profile_dir / lock_name
                        if lock_file.exists():
                            try:
                                lock_file.unlink()
                            except Exception:
                                pass

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
                    if self.proxy and str(self.proxy).strip() and str(self.proxy).strip() != "nan":
                        options.add_argument(f"--proxy-server={str(self.proxy).strip()}")

                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)

                    # Apply CDP Anti-Detection Stealth Patches
                    try:
                        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                            "source": """
                                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                                window.chrome = { runtime: {} };
                                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                            """
                        })
                    except Exception:
                        pass

                    with active_drivers_lock:
                        ACTIVE_DRIVERS.append(driver)

                    marker = profile_dir / "First_Login_Done.txt"
                    if not marker.exists():
                        raise Exception(f"Account {email} is not logged in yet. Please log in first via Manage Accounts.")

                    # ── 3. Pre-Flight Health & Previous Listing Review Check (On 2nd+ listing or re-opened ID) ──
                    if idx > 0 and attempt == 1:
                        update_account_state(email, state="CHECKING", details="Checking previous listing & account health...")
                        is_healthy, flag_reason = check_account_health_and_previous_listing(driver)
                        if not is_healthy:
                            flag_account(email, flag_reason, title)
                            log_live_message(f"🚨 [{email}] Flagged during health check: {flag_reason}! Closing profile and skipping.")
                            update_account_state(email, state="FLAGGED", details=f"Flagged: {flag_reason}")
                            self.failed_listings.append(f"{title} (🚨 FLAGGED: {flag_reason})")
                            listing_succeeded = True  # Mark as handled so the outer "failed" check doesn't double-add
                            break  # Don't retry flagged accounts

                    update_account_state(email, state="NAVIGATING", details="Navigating to Facebook Marketplace...")
                    check = move_to_path(driver)
                    if not check:
                        # Organic entry: visit Facebook home first, simulate brief scroll, then go to marketplace
                        driver.get("https://www.facebook.com")
                        time.sleep(random.randint(3, 5))
                        try:
                            driver.find_element("tag name", "body").send_keys(Keys.PAGE_DOWN)
                        except Exception:
                            pass
                        time.sleep(random.randint(2, 4))
                        driver.get("https://www.facebook.com/marketplace/create/item")
                    else:
                        driver.refresh()

                    time.sleep(5)

                    # ── Extract and Persist Facebook Account Profile Name ──
                    try:
                        from account_names import extract_fb_name_from_driver, save_account_fb_name
                        scraped_name = extract_fb_name_from_driver(driver)
                        if scraped_name:
                            save_account_fb_name(email, scraped_name)
                            if self.phone:
                                save_account_fb_name(self.phone, scraped_name)
                            self.fb_name = scraped_name
                    except Exception:
                        pass
                    display_id = self.fb_name or email

                    (img_entries, title_entry, description_entry, category_entry, location_entry,
                     tags_entry, price_entry, condition_entry, availability_entry, video_entry, wrapper, opt_vars) = entry

                    post_title = title_entry.get()
                    price = price_entry.get()
                    category = category_entry.get()
                    condition = condition_entry.get()
                    description = description_entry.get("1.0", "end").strip()
                    availability = availability_entry.get()
                    product_tags = [tag.strip() for tag in tags_entry.get().split(",") if tag.strip()]
                    images = [img.get() for img in img_entries if img.get()]
                    video = video_entry.get().strip()

                    # ── Image Duplicate Check (warn if image already used on this account) ──
                    if attempt == 1:  # Only warn on first attempt, not retries
                        img_warnings = check_image_usage(images, email)
                        for w in img_warnings:
                            log_live_message(f"⚠️ [{display_id}] {w} — proceeding but Facebook may detect duplicate.")

                    update_account_state(email, state="POSTING", details=f"Posting '{post_title}' (attempt {attempt}/{MAX_RETRIES})...", fb_name=self.fb_name)
                    result = go_to_items(
                        driver=driver,
                        title=post_title,
                        price=price,
                        category=category,
                        condition=condition,
                        description=description,
                        availability=availability,
                        product_tags=product_tags,
                        location=loc,
                        images=images,
                        video=video,
                        public_meetup=opt_vars[0].get(),
                        door_meetup=opt_vars[1].get(),
                        door_dropoff=opt_vars[2].get(),
                        marketplace_location=self.marketplace_location
                    )

                    if result:
                        listing_succeeded = True
                        log_live_message(f"✅ [{display_id}] Listing '{post_title}' published successfully!")
                        set_file_status(post_title, email)
                        # Record image usage for future deduplication
                        record_image_usage(images, email)
                        with _status_lock:
                            LIVE_BOT_STATE["completed_listings"] += 1
                        update_account_state(email, state="SIMULATING", details="Post-listing human simulation...", fb_name=self.fb_name)

                        # ── 4. Post-Listing Randomized Human Simulation ──
                        simulate_random_human_activity(driver, self.stop_event)
                        update_account_state(email, state="APPROVED", details=f"Published: '{post_title}'", fb_name=self.fb_name)
                    else:
                        log_live_message(f"❌ [{display_id}] go_to_items returned False for '{post_title}' (attempt {attempt}/{MAX_RETRIES}).")
                        if attempt < MAX_RETRIES:
                            log_live_message(f"⏳ [{email}] Waiting 15s before retry...")
                            update_account_state(email, state="COOLDOWN", details=f"Retry cooldown before attempt {attempt + 1}...")
                            _interruptible_sleep(15, self.stop_event, email=email, state_label="Pre-Retry Wait")

                except Exception as e:
                    log_live_message(f"🚨 [{email}] Error on attempt {attempt}/{MAX_RETRIES}: {e}")
                    err_detail = str(e)[:80]
                    update_account_state(email, state="ERROR", details=f"Attempt {attempt} error: {err_detail}")
                    if attempt < MAX_RETRIES:
                        log_live_message(f"⏳ [{email}] Waiting 20s before retry {attempt + 1}...")
                        update_account_state(email, state="COOLDOWN", details=f"Waiting before retry {attempt + 1}...")
                        _interruptible_sleep(20, self.stop_event, email=email, state_label="Pre-Retry Wait")

                finally:
                    # Always quit the driver after each attempt; a new one is opened on retry
                    if driver is not None:
                        with active_drivers_lock:
                            if driver in ACTIVE_DRIVERS:
                                ACTIVE_DRIVERS.remove(driver)
                        try:
                            driver.quit()
                        except Exception:
                            pass

                # If succeeded, stop retrying
                if listing_succeeded:
                    break

            # After all retry attempts exhausted without success
            if not listing_succeeded:
                err_short = title[:50]
                log_live_message(f"💀 [{email}] All {MAX_RETRIES} attempts failed for '{err_short}'. Marking as failed.")
                self.failed_listings.append(title)
                update_account_state(email, state="FAILED", details=f"All retries exhausted for '{err_short}'")

            # Release the concurrency semaphore slot (acquired once per listing at the top of the outer loop)
            with _status_lock:
                LIVE_BOT_STATE["active_browsers"] = max(0, LIVE_BOT_STATE["active_browsers"] - 1)
                if email in LIVE_BOT_STATE["accounts"]:
                    LIVE_BOT_STATE["accounts"][email]["browser_open"] = False

            if self.semaphore:
                try:
                    self.semaphore.release()
                except ValueError:
                    pass



            # If there are more listings scheduled for this account and no flags, enter cooldown
            if idx < len(self.assigned_entries) - 1:
                log_live_message(f"⏳ [{email}] Entering Cooldown ({self.time_sleep_cooldown}s) before next listing...")
                if not _interruptible_sleep(self.time_sleep_cooldown, self.stop_event, email=email, state_label="Account Cooldown"):
                    log_live_message(f"🛑 [{email}] Cooldown stopped by user.")
                    return


        # ── Final Worker Summary ──
        if len(self.failed_listings) == 0:
            update_account_state(email, state="COMPLETED", details="All assigned listings finished ✅")
            log_live_message(f"🎉 [{email}] Worker completed all tasks successfully.")
        else:
            failed_count = len(self.failed_listings)
            total = len(self.assigned_entries)
            update_account_state(email, state="COMPLETED_WITH_ERRORS", details=f"{failed_count}/{total} listings failed ⚠️")
            log_live_message(f"⚠️ [{email}] Worker finished with {failed_count} failed listing(s) out of {total}.")




# ── Multi-Account Orchestrator ──────────────────────────────────────────────

def run_orchestrator(
    entries: list,
    time_sleep: int = 1800,
    wait_time_accounts: int = 2,
    marketplace_location: str = "UK",
    wait_for_review: bool = False,
    max_concurrent_browsers: int = 2,
    stop_event: Optional[threading.Event] = None,
    max_review_timeout: int = 1800,
    distribution_mode: str = "round_robin"
) -> Dict[str, list]:
    """
    Asynchronous Multi-Account Orchestrator.
    Manages accounts concurrently with worker threads and a concurrency semaphore.
    """
    if stop_event is None:
        stop_event = threading.Event()

    accounts = read_multiple_credentials(CSV_PATH)
    if not accounts:
        log_live_message("⚠️ No accounts found in emails.csv. Please add accounts first.")
        return {}

    # ── Load existing completion state (do NOT delete saved_states.csv) ──
    # Build a set of already-completed (title, email) pairs so we can skip them.
    already_done: set = set()
    CSV_COLUMNS = [
        "Name", "Status", "Title", "Price", "Category", "Condition", "Description",
        "Availability", "Product_Tags", "Images", "Video", "public_meetup",
        "door_dropoff", "door_meetup", "Location", "Market_Location"
    ]
    if os.path.exists(saved_states_file):
        try:
            prev_df = pd.read_csv(saved_states_file, dtype=str).fillna("")
            for _, row in prev_df.iterrows():
                status_val = str(row.get("Status", "")).strip().lower()
                if status_val in ("true", "1", "yes"):
                    already_done.add(str(row.get("Name", "")))
        except Exception:
            prev_df = pd.DataFrame(columns=CSV_COLUMNS)
    else:
        prev_df = pd.DataFrame(columns=CSV_COLUMNS)
        prev_df.to_csv(saved_states_file, index=False)

    if already_done:
        log_live_message(f"⏭️ Resuming session: {len(already_done)} listing(s) already completed — will be skipped.")

    # Distribute entries among accounts via Interleaved Round-Robin:
    # Account 0 gets listings [0, N, 2N, ...] -> Listing 1, Listing 3, Listing 5...
    # Account 1 gets listings [1, N+1, 2N+1, ...] -> Listing 2, Listing 4, Listing 6...
    # Wave 1 posts Listing 1 (ID 1) & Listing 2 (ID 2).
    # After 30m cooldown, Wave 2 posts Listing 3 (ID 1) & Listing 4 (ID 2).
    n_accounts = len(accounts)
    assigned_buckets = [[] for _ in range(n_accounts)]
    for idx, entry in enumerate(entries):
        assigned_buckets[idx % n_accounts].append(entry)
    assignments = list(zip(accounts, assigned_buckets))

    # Populate saved_states — only add rows for listings NOT already in the CSV
    existing_names: set = set()
    try:
        existing_df = pd.read_csv(saved_states_file, dtype=str).fillna("")
        existing_names = set(existing_df["Name"].tolist())
    except Exception:
        pass

    for account, assigned in assignments:
        for entry in assigned:
            loc = entry[4].get() if len(entry) > 4 else ""
            title = entry[1].get() if len(entry) > 1 else ""
            unique_name = title + '||||' + str(account[0])
            if unique_name not in existing_names:
                make_files(entry, account[0], loc, marketplace_location)
                existing_names.add(unique_name)

    # Filter each bucket: remove entries already successfully completed for this account
    filtered_assignments = []
    for account, assigned in assignments:
        email = account[0]
        filtered = []
        for entry in assigned:
            title = entry[1].get() if len(entry) > 1 else ""
            unique_name = title + '||||' + str(email)
            if unique_name in already_done:
                log_live_message(f"⏭️ [{email}] Skipping '{title}' — already posted successfully.")
            else:
                filtered.append(entry)
        filtered_assignments.append((account, filtered))
    assignments = filtered_assignments

    # Initialize Live Status
    with _status_lock:
        LIVE_BOT_STATE["status"] = "running"
        LIVE_BOT_STATE["active_browsers"] = 0
        LIVE_BOT_STATE["max_concurrent"] = max_concurrent_browsers
        LIVE_BOT_STATE["completed_listings"] = 0
        LIVE_BOT_STATE["total_listings"] = sum(len(a[1]) for a in assignments)
        LIVE_BOT_STATE["accounts"] = {}
        LIVE_BOT_STATE["logs"] = []
        for account, assigned in assignments:
            LIVE_BOT_STATE["accounts"][account[0]] = {
                "email": account[0],
                "state": "QUEUED",
                "details": f"Assigned {len(assigned)} listings",
                "stage": "QUEUED",
                "elapsed_mins": 0.0,
                "cooldown_remaining": 0,
                "active_listing": "",
                "browser_open": False
            }

    total = LIVE_BOT_STATE['total_listings']
    log_live_message(f"🚀 Launching Orchestrator: {len(accounts)} Accounts, {total} Total Listings, Max {max_concurrent_browsers} Concurrent Browsers")

    semaphore = threading.Semaphore(max_concurrent_browsers)
    workers: List[AccountLifecycleWorker] = []

    for account_idx, (account, assigned) in enumerate(assignments):
        if not assigned:
            continue

        loc_list = []
        for entry in assigned:
            if len(entry) > 4:
                loc_raw = entry[4].get()
                loc_splits = [s.strip() for s in loc_raw.split("|") if s.strip()]
                if loc_splits:
                    loc_list.append(loc_splits[account_idx % len(loc_splits)])
                else:
                    loc_list.append(loc_raw.strip())
            else:
                loc_list.append("")

        worker = AccountLifecycleWorker(
            account_tuple=account,
            assigned_entries=assigned,
            location_list=loc_list,
            marketplace_location=marketplace_location,
            time_sleep_cooldown=time_sleep,
            wait_time_accounts=wait_time_accounts,
            wait_for_review=wait_for_review,
            stop_event=stop_event,
            semaphore=semaphore,
            max_review_timeout=max_review_timeout
        )
        workers.append(worker)



    # Stagger launch of worker threads with randomized jitter
    for w_idx, worker in enumerate(workers):
        if stop_event.is_set():
            break
        worker.start()
        # Don't sleep after the last worker
        if w_idx < len(workers) - 1:
            jitter = random.randint(30, 90)
            stagger_total = wait_time_accounts + jitter
            log_live_message(f"⏳ Staggering next account launch by {stagger_total}s ({wait_time_accounts}s configured + {jitter}s jitter)...")
            if not _interruptible_sleep(stagger_total, stop_event, state_label="Inter-Account Launch Stagger"):
                break

    # Monitor all workers until completion
    for worker in workers:
        while worker.is_alive():
            if stop_event.is_set():
                break
            worker.join(timeout=1.0)

    not_gen = {}
    for worker in workers:
        if worker.failed_listings:
            not_gen[worker.email] = worker.failed_listings

    with _status_lock:
        LIVE_BOT_STATE["status"] = "idle"
        LIVE_BOT_STATE["failed"] = not_gen

    log_live_message("🏁 Orchestrator finished all account workflows.")
    return not_gen



def main(entries, time_sleep=1800, wait_time_accounts=2, marketplace_location="UK", stop_event=None):
    return run_orchestrator(
        entries=entries,
        time_sleep=time_sleep,
        wait_time_accounts=wait_time_accounts,
        marketplace_location=marketplace_location,
        stop_event=stop_event,
        distribution_mode="interleaved"
    )

run_fb_bot = main


def distribute_among_accounts(entries, time_sleep=1800, wait_time_accounts=2, marketplace_location="UK", stop_event=None):
    return run_orchestrator(
        entries=entries,
        time_sleep=time_sleep,
        wait_time_accounts=wait_time_accounts,
        marketplace_location=marketplace_location,
        stop_event=stop_event,
        distribution_mode="interleaved"
    )


if __name__ == "__main__":
    main([])