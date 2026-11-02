import os
import json
import socket
import psutil
import subprocess
import time
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

BUNDLED_IX_CHROMEDRIVER = os.path.expandvars(r"%APPDATA%\ixBrowser-Resources\chrome\148-0007\chromedriver.exe")
IX_BROWSER_DATA_DIR = r"D:\IX Browser\Browser Data"

KNOWN_PROFILES = {
    "846fa927cf3f62f5819ca59f71428d24": {"name": "Anton Dixon", "profile_id": "5"},
    "5a18f1ff0960dc79187626406b9c8a9c": {"name": "Felix Bronson", "profile_id": "3"},
}

def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.2) -> bool:
    """Fast check if a local port is actively listening."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False

def bring_window_to_foreground(title_contains: str = "facebook"):
    """Brings any open window matching title_contains to the foreground."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        def enum_handler(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if title_contains.lower() in buff.value.lower():
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
    except Exception as e:
        print(f"[ix_detector] Focus window notice: {e}")


class IXBrowserManager:
    """
    Direct-Process & Taskbar discovery manager for ixBrowser profiles.
    - Scans running processes on the system to detect open profiles immediately.
    - Resolves active CDP ports or seamlessly activates port without losing tabs/session.
    - Attaches Selenium via CDP with stealth patches.
    - NEVER closes windows or tabs.
    """

    def __init__(self):
        self.data_dir = IX_BROWSER_DATA_DIR

    def get_opened_profiles(self) -> List[Dict[str, Any]]:
        """
        Detects open ixBrowser profiles by directly checking running system processes.
        Matches Chrome kernel instances by their profile user-data-dir.
        """
        opened = []
        seen_hashes = set()

        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                if 'chrome' not in name:
                    continue

                cmdline = p.info.get('cmdline') or []
                cmd_str = ' '.join(cmdline).lower()

                # Filter child processes like renderer, gpu, utility
                if '--type=' in cmd_str:
                    continue

                for p_hash, meta in KNOWN_PROFILES.items():
                    if p_hash.lower() in cmd_str and p_hash not in seen_hashes:
                        seen_hashes.add(p_hash)
                        profile_dir = os.path.join(self.data_dir, p_hash)
                        dt_file = os.path.join(profile_dir, "DevToolsActivePort")

                        debug_port = None
                        # Check cmdline arg first
                        for arg in cmdline:
                            if arg.startswith("--remote-debugging-port="):
                                val = arg.split("=")[1].strip()
                                if val.isdigit() and int(val) > 0:
                                    debug_port = int(val)

                        # Check DevToolsActivePort file
                        if not debug_port and os.path.exists(dt_file):
                            try:
                                with open(dt_file, "r", encoding="utf-8") as f:
                                    line = f.readline().strip()
                                    if line.isdigit() and is_port_listening(int(line)):
                                        debug_port = int(line)
                            except Exception:
                                pass

                        opened.append({
                            "profile_id": meta["profile_id"],
                            "name": meta["name"],
                            "fb_name": meta["name"],
                            "hash": p_hash,
                            "pid": p.info['pid'],
                            "cmdline": cmdline,
                            "debugging_port": debug_port,
                            "debugging_address": f"127.0.0.1:{debug_port}" if debug_port else None,
                            "webdriver": BUNDLED_IX_CHROMEDRIVER if os.path.exists(BUNDLED_IX_CHROMEDRIVER) else None,
                            "source": "process_scan"
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Fallback: Check active DevToolsActivePort files if process scan didn't catch them
        if not opened and os.path.exists(self.data_dir):
            for dir_name in os.listdir(self.data_dir):
                if dir_name in seen_hashes:
                    continue
                dt_file = os.path.join(self.data_dir, dir_name, "DevToolsActivePort")
                if os.path.exists(dt_file):
                    try:
                        with open(dt_file, "r", encoding="utf-8") as f:
                            line = f.readline().strip()
                        if line.isdigit() and is_port_listening(int(line)):
                            meta = KNOWN_PROFILES.get(dir_name, {"name": f"ixProfile_{dir_name[:6]}", "profile_id": dir_name[:6]})
                            opened.append({
                                "profile_id": meta["profile_id"],
                                "name": meta["name"],
                                "fb_name": meta["name"],
                                "hash": dir_name,
                                "pid": None,
                                "cmdline": None,
                                "debugging_port": int(line),
                                "debugging_address": f"127.0.0.1:{line}",
                                "webdriver": BUNDLED_IX_CHROMEDRIVER if os.path.exists(BUNDLED_IX_CHROMEDRIVER) else None,
                                "source": "devtools_port_file"
                            })
                    except Exception:
                        pass

        return opened

    def ensure_debugging_port(self, profile: Dict[str, Any]) -> Optional[str]:
        """
        Ensures the profile has an active CDP debugging port.
        If already active, returns it immediately.
        If not, restarts the process with --remote-debugging-port=0 (keeping session and tabs intact).
        """
        if profile.get("debugging_address") and profile.get("debugging_port"):
            if is_port_listening(profile["debugging_port"]):
                return profile["debugging_address"]

        pid = profile.get("pid")
        cmdline = profile.get("cmdline")
        p_hash = profile.get("hash")
        profile_dir = os.path.join(self.data_dir, p_hash)
        dt_file = os.path.join(profile_dir, "DevToolsActivePort")

        if not pid or not cmdline:
            return None

        try:
            p = psutil.Process(pid)
            new_cmd = list(cmdline)
            if not any(arg.startswith("--remote-debugging-port=") for arg in new_cmd):
                new_cmd.insert(1, "--remote-debugging-port=0")

            p.terminate()
            try:
                p.wait(timeout=3)
            except Exception:
                p.kill()

            DETACHED = 0x00000008
            NEW_GROUP = 0x00000200
            new_p = subprocess.Popen(new_cmd, creationflags=DETACHED | NEW_GROUP, close_fds=True)

            for _ in range(25):
                time.sleep(0.2)
                if os.path.exists(dt_file):
                    try:
                        with open(dt_file, "r", encoding="utf-8") as f:
                            line = f.readline().strip()
                        if line.isdigit() and is_port_listening(int(line)):
                            profile["debugging_port"] = int(line)
                            profile["debugging_address"] = f"127.0.0.1:{line}"
                            profile["pid"] = new_p.pid
                            return profile["debugging_address"]
                    except Exception:
                        pass
        except Exception as e:
            print(f"[ix_detector] Error enabling debugging port: {e}")

        return None

    def get_all_detected_profiles(self) -> List[Dict[str, Any]]:
        """
        Returns all registered ixBrowser profiles, marking their open/active status.
        Used by the UI to show the user which accounts are open vs offline.
        """
        opened_list = self.get_opened_profiles()
        opened_hashes = {p["hash"] for p in opened_list}

        all_profiles = list(opened_list)

        for p_hash, info in KNOWN_PROFILES.items():
            if p_hash not in opened_hashes:
                all_profiles.append({
                    "profile_id": info["profile_id"],
                    "name": info["name"],
                    "fb_name": info["name"],
                    "hash": p_hash,
                    "debugging_address": None,
                    "debugging_port": None,
                    "webdriver": BUNDLED_IX_CHROMEDRIVER if os.path.exists(BUNDLED_IX_CHROMEDRIVER) else None,
                    "status": "Offline (Click Open in ixBrowser)",
                    "source": "registered"
                })

        return all_profiles

    def attach_driver(self, debugging_address: str, webdriver_path: Optional[str] = None) -> webdriver.Chrome:
        """
        Attaches Selenium Chrome WebDriver to the already-running
        ixBrowser profile via its CDP debugging address without closing or modifying tabs.
        """
        options = Options()
        options.add_experimental_option("debuggerAddress", debugging_address)
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver_exec = webdriver_path
        if not driver_exec or not os.path.exists(driver_exec):
            if os.path.exists(BUNDLED_IX_CHROMEDRIVER):
                driver_exec = BUNDLED_IX_CHROMEDRIVER

        if driver_exec and os.path.exists(driver_exec):
            service = Service(driver_exec)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        # Mark as ixBrowser so lifecycle hooks NEVER close it
        setattr(driver, "is_ix", True)
        setattr(driver, "ix_debugging_address", debugging_address)

        # Override quit and close to prevent accidental closure
        driver.quit = lambda: None
        driver.close = lambda: None

        # Apply stealth patches
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

        # Bring window into foreground
        try:
            bring_window_to_foreground("facebook")
        except Exception:
            pass

        return driver


# Singleton manager instance
ix_manager = IXBrowserManager()
