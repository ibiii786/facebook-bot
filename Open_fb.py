import os
import sys
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
    STATUS_APPROVED,
    STATUS_FLAGGED,
    STATUS_TIMEOUT,
    STATUS_IN_REVIEW
)
from login_profile import email_to_safe
from path import move_to_path
from save_state import make_files, set_file_status

CSV_PATH = "emails.csv"
saved_states_file = "saved_states.csv"


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


def update_account_state(email: str, state: str, details: str = "", stage: str = "", elapsed_mins: float = 0.0, cooldown_remaining: int = 0):
    with _status_lock:
        if email not in LIVE_BOT_STATE["accounts"]:
            LIVE_BOT_STATE["accounts"][email] = {
                "email": email,
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


# ── Account Worker Lifecycle Engine ─────────────────────────────────────────
class AccountLifecycleWorker(threading.Thread):
    def __init__(
        self,
        account_tuple: tuple,
        assigned_entries: list,
        location_list: list,
        marketplace_location: str = "UK",
        time_sleep_cooldown: int = 1800,
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
        self.wait_for_review = wait_for_review
        self.stop_event = stop_event or threading.Event()
        self.semaphore = semaphore
        self.max_review_timeout = max_review_timeout
        self.failed_listings = []

    def run(self):
        email = self.email
        log_live_message(f"🚀 Worker started for account: {email} ({len(self.assigned_entries)} listings assigned)")
        update_account_state(email, state="QUEUED", details=f"Queued ({len(self.assigned_entries)} listings)")

        for idx, entry in enumerate(self.assigned_entries):
            if self.stop_event.is_set():
                log_live_message(f"🛑 Worker stopped for {email}")
                update_account_state(email, state="STOPPED", details="Halted by user")
                return

            loc = self.location_list[idx % len(self.location_list)] if self.location_list else ""
            title = entry[1].get() if len(entry) > 1 else f"Listing #{idx+1}"

            # Acquire concurrency slot
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

            driver = None
            keep_browser_open = False
            try:
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
                with active_drivers_lock:
                    ACTIVE_DRIVERS.append(driver)


                marker = profile_dir / "First_Login_Done.txt"
                if not marker.exists():
                    raise Exception(f"Account {email} is not logged in yet. Please log in first via Manage Accounts.")

                update_account_state(email, state="NAVIGATING", details="Navigating to Facebook Marketplace...")
                check = move_to_path(driver)
                if not check:
                    driver.get("https://www.facebook.com/marketplace/create/item")
                else:
                    driver.refresh()

                time.sleep(5)

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

                def status_cb(data):
                    stg = data.get("stage", "")
                    el_m = data.get("elapsed_mins", 0.0)
                    chk = data.get("check_count", 0)
                    if stg == "REELS_WARMUP":
                        update_account_state(
                            email,
                            state="REELS_WARMUP",
                            details=f"Watching Reels ({el_m}m) | Check #{chk}",
                            stage="REELS",
                            elapsed_mins=el_m
                        )
                    elif stg == "CHECKING_REVIEW":
                        update_account_state(
                            email,
                            state="CHECKING_REVIEW",
                            details=f"Checking Marketplace Selling page ({el_m}m)...",
                            stage="REVIEW_CHECK",
                            elapsed_mins=el_m
                        )

                update_account_state(email, state="POSTING", details=f"Automating listing form for '{post_title}'")
                log_live_message(f"📝 [{email}] Posting listing: '{post_title}' (${price})")

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
                    marketplace_location=self.marketplace_location,
                    wait_for_review=self.wait_for_review,
                    stop_event=self.stop_event,
                    status_callback=status_cb,
                    max_review_timeout=self.max_review_timeout
                )

                if result == STATUS_APPROVED or result is True:
                    log_live_message(f"✅ [{email}] Listing '{post_title}' APPROVED & ACTIVE!")
                    set_file_status(post_title, email)
                    with _status_lock:
                        LIVE_BOT_STATE["completed_listings"] += 1
                    update_account_state(email, state="APPROVED", details=f"Approved & Live: '{post_title}'")

                elif result in [STATUS_FLAGGED, "REVIEW_STUCK"]:
                    log_live_message(f"⚠️ [{email}] Checkpoint / Flag detected on '{post_title}'! Leaving browser window open.")
                    keep_browser_open = True
                    self.failed_listings.append(f"{post_title} (⚠️ Flagged - Browser Left Open)")
                    update_account_state(email, state="FLAGGED", details="⚠️ Action Required: Browser left open for manual inspection", stage="FLAGGED")
                    break  # Halt further posts on this flagged account

                elif result == STATUS_TIMEOUT:
                    log_live_message(f"⌛ [{email}] Review timeout for '{post_title}'. Leaving browser open for safety.")
                    keep_browser_open = True
                    self.failed_listings.append(f"{post_title} (⌛ Review Timeout)")
                    update_account_state(email, state="TIMEOUT", details="⌛ Review Timeout: Browser open", stage="TIMEOUT")
                    break

                elif result == "STOPPED":
                    log_live_message(f"🛑 [{email}] Stopped during listing execution.")
                    update_account_state(email, state="STOPPED", details="Halted by user")
                    return

                else:
                    log_live_message(f"❌ [{email}] Failed to post '{post_title}'.")
                    self.failed_listings.append(post_title)
                    update_account_state(email, state="FAILED", details=f"Failed posting '{post_title}'")

            except Exception as e:
                log_live_message(f"🚨 [{email}] Error during execution: {e}")
                self.failed_listings.append(f"{title} (Error: {str(e)[:50]})")
                update_account_state(email, state="ERROR", details=f"Error: {str(e)[:60]}")

            finally:
                if driver is not None:
                    with active_drivers_lock:
                        if driver in ACTIVE_DRIVERS:
                            ACTIVE_DRIVERS.remove(driver)

                    if not keep_browser_open:
                        try:
                            driver.quit()
                        except Exception:
                            pass

                with _status_lock:
                    LIVE_BOT_STATE["active_browsers"] = max(0, LIVE_BOT_STATE["active_browsers"] - 1)
                    if email in LIVE_BOT_STATE["accounts"]:
                        LIVE_BOT_STATE["accounts"][email]["browser_open"] = keep_browser_open

                if self.semaphore:
                    try:
                        self.semaphore.release()
                    except ValueError:
                        pass


            # If there are more listings scheduled for this account and no flags, enter cooldown
            if idx < len(self.assigned_entries) - 1 and not keep_browser_open:
                log_live_message(f"⏳ [{email}] Entering Cooldown ({self.time_sleep_cooldown}s) before next listing...")
                if not _interruptible_sleep(self.time_sleep_cooldown, self.stop_event, email=email, state_label="Account Cooldown"):
                    log_live_message(f"🛑 [{email}] Cooldown stopped by user.")
                    return

        if not keep_browser_open:
            update_account_state(email, state="COMPLETED", details="All assigned listings finished ✅")
            log_live_message(f"🎉 [{email}] Worker completed all tasks successfully.")


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

    # Initialize CSV saved_states
    if os.path.exists(saved_states_file):
        try:
            os.remove(saved_states_file)
        except Exception:
            pass

    pd.DataFrame(columns=[
        "Name", "Status", "Title", "Price", "Category", "Condition", "Description",
        "Availability", "Product_Tags", "Images", "Video", "public_meetup",
        "door_dropoff", "door_meetup", "Location", "Market_Location"
    ]).to_csv(saved_states_file, index=False)

    # Distribute entries among accounts
    n_accounts = len(accounts)
    n_entries = len(entries)
    assignments = []

    if distribution_mode == "distribute_chunks":
        entries_per_account = n_entries // n_accounts
        remainder = n_entries % n_accounts
        i = 0
        for idx, account in enumerate(accounts):
            take = entries_per_account + (1 if idx < remainder else 0)
            assigned = entries[i:i+take] if take > 0 else []
            assignments.append((account, assigned))
            i += take
    else:
        # Default: All accounts get all entries or equal round-robin
        for account in accounts:
            assignments.append((account, list(entries)))

    # Populate saved_states files
    for account, assigned in assignments:
        for entry in assigned:
            loc = entry[4].get() if len(entry) > 4 else ""
            make_files(entry, account[0], loc, marketplace_location)

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

    log_live_message(f"🚀 Launching Orchestrator: {len(accounts)} Accounts, {LIVE_BOT_STATE['total_listings']} Total Listings, Max {max_concurrent_browsers} Concurrent Browsers")

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
            wait_for_review=wait_for_review,
            stop_event=stop_event,
            semaphore=semaphore,
            max_review_timeout=max_review_timeout
        )
        workers.append(worker)


    # Stagger launch of worker threads
    for worker in workers:
        if stop_event.is_set():
            break
        worker.start()
        time.sleep(wait_time_accounts)

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



# ── Backwards Compatible Entry Points ───────────────────────────────────────
def main(entries, time_sleep=1800, wait_time_accounts=2, marketplace_location="UK", wait_for_review=False, stop_event=None, max_concurrent_browsers=2):
    return run_orchestrator(
        entries=entries,
        time_sleep=time_sleep,
        wait_time_accounts=wait_time_accounts,
        marketplace_location=marketplace_location,
        wait_for_review=wait_for_review,
        max_concurrent_browsers=max_concurrent_browsers,
        stop_event=stop_event,
        distribution_mode="all"
    )


def distribute_among_accounts(entries, time_sleep=1800, wait_time_accounts=2, marketplace_location="UK", wait_for_review=False, stop_event=None, max_concurrent_browsers=2):
    return run_orchestrator(
        entries=entries,
        time_sleep=time_sleep,
        wait_time_accounts=wait_time_accounts,
        marketplace_location=marketplace_location,
        wait_for_review=wait_for_review,
        max_concurrent_browsers=max_concurrent_browsers,
        stop_event=stop_event,
        distribution_mode="distribute_chunks"
    )


if __name__ == "__main__":
    main([])