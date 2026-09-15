import os
import json
import socket
import psutil
import requests
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

try:
    from ixbrowser_local_api import IXBrowserClient
    HAS_IX_SDK = True
except ImportError:
    HAS_IX_SDK = False

BUNDLED_IX_CHROMEDRIVER = os.path.expandvars(r"%APPDATA%\ixBrowser-Resources\chrome\148-0007\chromedriver.exe")

def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.15) -> bool:
    """Ultra-fast check if a local port is listening (avoids HTTP connection hanging)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def get_ixbrowser_port() -> int:
    """Read configured port from ixBrowser roaming config or default to 53200."""
    roaming_config = os.path.expandvars(r"%APPDATA%\ixBrowser\config.json")
    if os.path.exists(roaming_config):
        try:
            with open(roaming_config, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "port" in data and int(data["port"]) > 0:
                    return int(data["port"])
        except Exception:
            pass
    return 53200


class IXBrowserManager:
    """
    High-reliability discovery and attachment manager for ixBrowser profiles.
    1. Fast-probes local API (port 53200) for native client opened profiles.
    2. Deep-scans running processes for ixBrowser Chrome kernels with DevToolsActivePort fallback.
    3. Attaches Selenium via CDP with anti-detection stealth without closing or altering tabs.
    """

    def __init__(self, port: Optional[int] = None):
        self.port = port or get_ixbrowser_port()
        self.client = IXBrowserClient(port=self.port) if HAS_IX_SDK else None

    def is_api_available(self) -> bool:
        """Fast-check if ixBrowser Local API is responsive (<10ms)."""
        if not is_port_listening(self.port):
            return False
        try:
            r = requests.get(f"http://127.0.0.1:{self.port}/api/v2/profile-opened-list", timeout=0.5)
            return r.status_code == 200
        except Exception:
            return False

    def get_opened_profiles(self) -> List[Dict[str, Any]]:
        """
        Retrieve list of currently open ixBrowser profiles.
        Queries native-client-profile-opened-list, standard opened-list,
        and falls back to process scanning.
        """
        opened = []

        if is_port_listening(self.port):
            # 1. Query Native Client profile opened list (used when opened via ixBrowser GUI)
            try:
                url = f"http://127.0.0.1:{self.port}/api/v2/native-client-profile-opened-list"
                res = requests.get(url, timeout=1.2).json()
                if res.get("error", {}).get("code") == 0:
                    raw_data = res.get("data", [])
                    if isinstance(raw_data, list):
                        for p in raw_data:
                            opened.append({
                                "profile_id": p.get("profile_id"),
                                "name": p.get("name") or f"ixProfile_{p.get('profile_id')}",
                                "debugging_address": p.get("debugging_address"),
                                "debugging_port": p.get("debugging_port"),
                                "pid": p.get("pid"),
                                "webdriver": p.get("webdriver") or (BUNDLED_IX_CHROMEDRIVER if os.path.exists(BUNDLED_IX_CHROMEDRIVER) else None),
                                "source": "api_native"
                            })
                        if opened:
                            return opened
            except Exception:
                pass

            # 2. Query standard opened profile list
            try:
                url = f"http://127.0.0.1:{self.port}/api/v2/profile-opened-list"
                res = requests.get(url, timeout=1.2).json()
                if res.get("error", {}).get("code") == 0:
                    raw_data = res.get("data", [])
                    if isinstance(raw_data, list):
                        for p in raw_data:
                            opened.append({
                                "profile_id": p.get("profile_id"),
                                "name": p.get("name") or f"ixProfile_{p.get('profile_id')}",
                                "debugging_address": p.get("debugging_address"),
                                "debugging_port": p.get("debugging_port"),
                                "pid": p.get("pid"),
                                "webdriver": p.get("webdriver") or (BUNDLED_IX_CHROMEDRIVER if os.path.exists(BUNDLED_IX_CHROMEDRIVER) else None),
                                "source": "api_standard"
                            })
                        if opened:
                            return opened
            except Exception:
                pass

        # 3. Fallback: Process table inspection for ixBrowser Chrome instances
        opened = self._scan_running_ix_processes()
        return opened

    def _scan_running_ix_processes(self) -> List[Dict[str, Any]]:
        """Detect running ixBrowser Chrome instances directly from process table."""
        found = []
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (p.info.get("name") or "").lower()
                cmdline = p.info.get("cmdline") or []
                cmd_str = " ".join(cmdline).lower()

                if "chrome" in name and ("ixbrowser" in cmd_str or "ix_browser" in cmd_str):
                    debug_port = None
                    user_data_dir = None

                    for arg in cmdline:
                        if arg.startswith("--remote-debugging-port="):
                            debug_port = arg.split("=")[1].strip()
                        elif arg.startswith("--user-data-dir="):
                            user_data_dir = arg.split("=")[1].strip()

                    # If port was 0 or not passed, inspect DevToolsActivePort in user-data-dir
                    if (not debug_port or debug_port == "0") and user_data_dir:
                        port_file = os.path.join(user_data_dir, "DevToolsActivePort")
                        if os.path.exists(port_file):
                            try:
                                with open(port_file, "r", encoding="utf-8") as f:
                                    first_line = f.readline().strip()
                                    if first_line.isdigit():
                                        debug_port = first_line
                            except Exception:
                                pass

                    if debug_port and debug_port != "0":
                        found.append({
                            "profile_id": p.info.get("pid"),
                            "name": f"ixBrowser Chrome ({p.info.get('pid')})",
                            "debugging_address": f"127.0.0.1:{debug_port}",
                            "debugging_port": debug_port,
                            "pid": p.info.get("pid"),
                            "webdriver": BUNDLED_IX_CHROMEDRIVER if os.path.exists(BUNDLED_IX_CHROMEDRIVER) else None,
                            "source": "process_scan"
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found

    def attach_driver(self, debugging_address: str, webdriver_path: Optional[str] = None) -> webdriver.Chrome:
        """
        Attaches a Selenium Chrome WebDriver instance to the already-running
        ixBrowser profile via its CDP debugging address without interfering with open tabs.
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

        # Tag this driver instance so lifecycles know not to close it
        setattr(driver, "is_ix", True)
        setattr(driver, "ix_debugging_address", debugging_address)

        # Apply stealth patches to ensure undetectable automation
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

        return driver


# Global singleton instance
ix_manager = IXBrowserManager()
