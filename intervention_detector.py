import time
import ctypes
import threading
from typing import Optional, Callable

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint)
    ]

class InterventionDetector:
    """
    High-precision Human Intervention Detector using Windows Native API (GetLastInputInfo).
    Detects physical mouse movement, clicks, and keystrokes.
    Provides configurable inactivity wait timers (e.g., 30s for listing, 60s for simulation)
    that reset automatically if user activity is detected again during the wait.
    """

    def __init__(self):
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._bot_active = False

    def get_idle_seconds(self) -> float:
        """Returns the number of seconds since the last physical human input (mouse/keyboard)."""
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if self._user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = self._kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
        return 9999.0

    def is_human_active(self, threshold_seconds: float = 1.5) -> bool:
        """Returns True if the human touched the mouse or keyboard within the threshold."""
        return self.get_idle_seconds() < threshold_seconds

    def wait_for_inactivity(
        self,
        required_idle_seconds: float,
        stop_event: Optional[threading.Event] = None,
        context_label: str = "Intervention",
        on_status: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Pauses execution and waits until the user has been completely inactive
        for `required_idle_seconds` continuously.
        
        If the human moves the mouse or presses a key at ANY point during the countdown,
        the timer immediately resets back to `required_idle_seconds`.
        
        Returns:
            True if user was inactive for the full duration and control can be resumed.
            False if stop_event was triggered.
        """
        print(f"👤 [Human Intervention] User activity detected during {context_label}! Yielding control to human.")
        print(f"⏳ Waiting for {int(required_idle_seconds)} seconds of continuous human inactivity...")

        while True:
            if stop_event and stop_event.is_set():
                return False

            idle = self.get_idle_seconds()

            if idle >= required_idle_seconds:
                print(f"✅ [Human Inactivity] {int(required_idle_seconds)}s of inactivity reached. Bot safely taking back control.")
                if on_status:
                    on_status("Resuming", 0)
                return True

            remaining = required_idle_seconds - idle
            if on_status:
                on_status(f"Human active — resuming after {int(remaining)}s inactivity", remaining)

            # Check every 250ms for snappy responsiveness
            time.sleep(0.25)


# Global singleton instance
intervention_detector = InterventionDetector()
