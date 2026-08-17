import sys
import json
import tkinter as tk
from tkinter import filedialog

def pick(dialog_type="files"):
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        root.lift()
        root.focus_force()
        root.update()

        result = []
        if dialog_type == "files":
            res = filedialog.askopenfilenames(
                parent=root,
                title="Select Image Files",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"), ("All Files", "*.*")]
            )
            result = list(res) if res else []
        elif dialog_type == "video":
            res = filedialog.askopenfilename(
                parent=root,
                title="Select Video File",
                filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv *.webm"), ("All Files", "*.*")]
            )
            result = [res] if res else []
        elif dialog_type == "folder":
            res = filedialog.askdirectory(parent=root, title="Select Directory / Folder")
            result = [res] if res else []

        root.destroy()
        return result
    except Exception as e:
        sys.stderr.write(f"File picker error: {e}\n")
        return []

if __name__ == "__main__":
    dtype = sys.argv[1] if len(sys.argv) > 1 else "files"
    paths = pick(dtype)
    print("PICKER_OUTPUT:" + json.dumps(paths))
