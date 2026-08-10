import tkinter as tk
from Assets.Utils.Video.Video_controls import handle_drop_video, browse_video
from Assets.Constants.const import bg_color,main_color
from tkinterdnd2 import DND_FILES
def create_video_entry(parent,row, col):
        video_frame=tk.Frame(parent, bg=main_color)
        video_frame.grid(row=row, column=col, sticky="ew", padx=5,pady=5)
        video_label = tk.Label(video_frame, text="Video URL/Path", bg="#1e1e1e", fg="white")
        video_label.pack(padx=5, pady=5)
        video_entry = tk.Text(video_frame, bg=bg_color, fg="white", insertbackground="white", width=25,height=4)
        video_entry.pack(side="left", padx=3, pady=5)
        tk.Button(video_frame, text="Browse",width=15, command=lambda: browse_video(video_entry,is_text_box=True),
                  bg="#007acc", fg="white", relief="flat").pack(side="bottom", padx=5)
        drop_label_video = tk.Label(video_frame, text="📂 Drag & Drop", fg="#ccc", bg="#2d2d30",
                              font=("Segoe UI", 10, "italic"), width=15, height=2, relief="ridge")
        drop_label_video.pack(side="left", padx=5)
        drop_label_video.drop_target_register(DND_FILES)
        drop_label_video.dnd_bind('<<Drop>>', lambda e: handle_drop_video(e, video_entry,is_text_box=True))
        return video_entry