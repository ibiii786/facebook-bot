import os
import json
import re
import threading
from typing import Optional, Dict

_LOCK = threading.Lock()
ACCOUNT_NAMES_FILE = "account_names.json"

DEFAULT_SEEDED_NAMES = {
    "+13658659037": "Felix Navidad",
    "shane11872026@outlook.com": "Shane Shane"
}

def _get_storage_path() -> str:
    """Returns the path to account_names.json, creating it if needed."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, ACCOUNT_NAMES_FILE)

def load_account_names() -> Dict[str, str]:
    """Loads the account names dictionary from disk."""
    path = _get_storage_path()
    with _LOCK:
        if not os.path.exists(path):
            data = dict(DEFAULT_SEEDED_NAMES)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return data
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = dict(DEFAULT_SEEDED_NAMES)
                # Ensure seeded names are preserved
                for k, v in DEFAULT_SEEDED_NAMES.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return dict(DEFAULT_SEEDED_NAMES)

def save_account_fb_name(identifier: str, fb_name: str) -> None:
    """Saves or updates the Facebook profile name for an account identifier (email/phone)."""
    if not identifier or not fb_name:
        return
    clean_id = str(identifier).strip()
    clean_name = str(fb_name).strip()
    if not clean_id or not clean_name or clean_name.lower() in ("facebook", "unknown", "none", "null"):
        return

    path = _get_storage_path()
    with _LOCK:
        data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[clean_id] = clean_name
        # Also map without @domain if it's an email, for fallback matching
        if "@" in clean_id:
            user_part = clean_id.split("@")[0]
            data[user_part] = clean_name
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[account_names] Error saving {path}: {e}")

def get_account_fb_name(identifier: str) -> str:
    """Returns the Facebook Profile Name for an email or phone, or a clean fallback."""
    if not identifier:
        return "Unknown"
    clean_id = str(identifier).strip()
    names = load_account_names()
    if clean_id in names and names[clean_id]:
        return names[clean_id]
    # Check lowercase
    for k, v in names.items():
        if k.lower() == clean_id.lower():
            return v
    # Check user part if email
    if "@" in clean_id:
        user_part = clean_id.split("@")[0]
        if user_part in names and names[user_part]:
            return names[user_part]
    # Fallback to email username or phone
    if "@" in clean_id:
        return clean_id.split("@")[0]
    return clean_id

def get_all_account_names() -> Dict[str, str]:
    """Returns a full copy of the account names dictionary."""
    return load_account_names()

def extract_fb_name_from_driver(driver) -> Optional[str]:
    """
    Extracts the Facebook profile name from an open Chrome session.
    Non-intrusive, executes in <20ms using CurrentUserInitialData and DOM selectors.
    """
    if not driver:
        return None
    try:
        # 1. Fast JS extraction from CurrentUserInitialData or DOM
        name = driver.execute_script("""
            try {
                // Method A: Check CurrentUserInitialData in script tags
                for (const s of document.querySelectorAll('script')) {
                    const t = s.textContent || '';
                    const m = t.match(/"NAME"\\s*:\\s*"([^"]+)"/);
                    if (m && m[1] && m[1].toLowerCase() !== 'facebook') {
                        return m[1];
                    }
                }
                // Method B: Check profile navigation links
                const selectors = [
                    'a[aria-label="Your profile"] span',
                    'div[aria-label="Your profile"] span',
                    'a[href*="/me/"] span',
                    'a[href*="/me"] span',
                    'div[role="navigation"] a[role="link"] span'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent && el.textContent.trim()) {
                        const txt = el.textContent.trim();
                        if (txt && !['home', 'marketplace', 'groups', 'gaming', 'video', 'friends', 'feeds', 'facebook'].includes(txt.toLowerCase())) {
                            return txt;
                        }
                    }
                }
            } catch(e) {}
            return null;
        """)
        if name and str(name).strip() and str(name).strip().lower() != "facebook":
            return str(name).strip()

        # 2. Fallback regex on page_source
        src = driver.page_source
        match = re.search(r'"NAME"\s*:\s*"([^"]+)"', src)
        if match and match.group(1) and match.group(1).lower() != "facebook":
            return match.group(1).strip()
    except Exception as e:
        print(f"[account_names] Name extraction notice: {e}")
    return None
