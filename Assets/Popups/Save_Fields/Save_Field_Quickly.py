import tkinter as tk
from Assets.Constants.const import bg_color,main_color
from Assets.Files.SaveFiles.SaveFile import add_to_prev
from Assets.Popups.Fields.EnterSavedField import make_enter_saved_field_popup
from Assets.Utils.ImageHandling.Handle_image import add_image_box, browse_image
from Assets.Utils.Video.Video_entry import create_video_entry
import pandas as pd
text_fields = [ "Title", "Price", "Category", "Condition", "Description", "Availability", "Tags", "Images", "Video", "Location","Public meetup", "Door dropoff", "Door pickup"]

class StateWrapper:
    def __init__(self):
        self.img_arr = {}
        self.add_img_btn = {}
states=[]
def create_image_wrapper(current_state,field_grid,row,col):
    img_frame=tk.Frame(field_grid, bg=bg_color, height=2)
    img_frame.grid(row=row, column=col, padx=5, pady=5,columnspan=4, sticky="nsew")
    if img_frame not in current_state.img_arr:
        current_state.img_arr[img_frame]=[]
    add_img_btn = tk.Button(
        img_frame,
        text="➕ Add Image",
        bg="#2e8b57",
        fg="white",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        )
    add_img_btn.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
    current_state.add_img_btn[img_frame]=add_img_btn
    img_entry,img_row=add_image_box(current_state, img_frame,px=5,max_images=11)
    add_img_btn.config(
    command=lambda e=img_entry, r=img_row: browse_image(current_state, e, r,(90,90),False,11)
)
def delete_last_image_wrapper():
    global row, save_field_btn
    if not states:
        return
    last_state = states[-1]
    # Destroy all img_frames belonging to the last state
    for img_frame in list(last_state.img_arr.keys()):
        img_frame.destroy()
    states.pop()
    row -= 1
    save_field_btn.grid(row=row + 1, column=0, pady=10)
def create_text_field(root,label_text,row,column):
    frame=tk.Frame(root, bg=main_color, height=2)
    frame.grid(row=row, column=column, sticky="ew", padx=10,pady=10)
    label = tk.Label(frame, text=label_text, bg="#1e1e1e", fg="white")
    label.pack(padx=5, pady=5)
    entry = tk.Text(frame,height=4,width=40, bg=bg_color, fg="white", insertbackground="white")
    entry.pack(padx=5, pady=5)
    return entry
def on_modified(entry, field_grid, text_entries,character):
    entry.after(10, lambda: _do_on_modified(text_entries, field_grid,character))

def _do_on_modified(text_entries, field_grid,character):
    global row, save_field_btn
    max_lines = max(
        len(entry.get("1.0", "end-1c").split('|||' if field == 'Description' else '\n'))
        for field, entry in text_entries.items()
        if entry is not None
    )

    while max_lines > len(states):
        current_state = StateWrapper()
        states.append(current_state)
        create_image_wrapper(current_state, field_grid, row + 1, 0)
        row += 1
        save_field_btn.grid(row=row + 1, column=0, pady=10)
    while max_lines < len(states):
        delete_last_image_wrapper()


def save_field(text_entries, self):
    field_data = {}
    character='\n'
    for field, entry in text_entries.items():
        if field=='Description':
            character='|||'
        else:
            character='\n'
        if field=="Images":
            images_list = []
            for state in states:
                for _, img_entries in state.img_arr.items():
                    single_img_list = []
                    for img_entry in img_entries:
                        img_path = img_entry.get()
                        if img_path:
                            single_img_list.append(img_path)
                images_list.append(single_img_list)
                print("Images List:", images_list) 
   # Debug print
            field_data[field] = images_list
            continue
        text = entry.get("1.0", "end-1c")  # -1c removes trailing newline
        lines = [line.strip() for line in text.split(character) if line.strip()]  # remove empty lines
        if field=="Tags":
            items_list=[f.split(",") for f in lines]
            field_data[field] = items_list
            continue
        field_data[field] = lines

    # Find max rows
    max_rows = max(len(v) for v in field_data.values())

    # Pad shorter fields with None
    for field in field_data:
        while len(field_data[field]) < max_rows:
            field_data[field].append(None)

    df = pd.DataFrame(field_data)
    def callback(file_path):
        add_to_prev(df,file_path)
    make_enter_saved_field_popup(self, callback)
def save_field_quickly_interface(self):
    save_window = tk.Toplevel(self)
    save_window.title("Save Field Quickly")
    save_window.configure(bg=bg_color)
    save_window.grab_set()
    
    # ── Scrollable scaffold ──────────────────────────────────────────────
    save_window.geometry("1500x650")  # Fixed starting size
    save_window.resizable(True, False)  # 
    # ── Scrollable scaffold ──────────────────────────────────────────────
    outer_frame = tk.Frame(save_window, bg=bg_color)
    outer_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer_frame, bg=bg_color, highlightthickness=0)
    v_scrollbar = tk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
    h_scrollbar = tk.Scrollbar(save_window, orient="horizontal", command=canvas.xview)

    canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

    h_scrollbar.pack(side="bottom", fill="x")
    v_scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # Inner frame lives inside the canvas
    inner_frame = tk.Frame(canvas, bg=bg_color)
    canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

    # Resize scroll region whenever inner_frame changes size
    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)

    inner_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    # Mouse-wheel scrolling (works on Windows & Linux)
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_mousewheel_linux(event):
        if event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")

    save_window.bind("<MouseWheel>", on_mousewheel)          # Windows / macOS
    save_window.bind("<Button-4>", on_mousewheel_linux)      # Linux scroll up
    save_window.bind("<Button-5>", on_mousewheel_linux)      # Linux scroll down
    # ────────────────────────────────────────────────────────────────────

    label = tk.Label(inner_frame, text="Save fields Quickly", bg=bg_color, fg="white", font=("Arial", 14))
    label.pack(pady=10)
    field_grid = tk.Frame(inner_frame, bg=bg_color)
    field_grid.pack(padx=10, pady=10)

    text_entries = {}
    def unbind_scroll():
        save_window.destroy()

    save_window.protocol("WM_DELETE_WINDOW", unbind_scroll)
    global row
    global col
    row=0 
    col=0 

    for field in text_fields:
        if field=="Images":
            text_entries[field] = None 
            continue
        if field=="Video":
            text_entries[field] = None
            continue
        entry = create_text_field(field_grid, field, row, col)
        text_entries[field] = entry
        col += 1
        if col > 3:
            col = 0
            row += 1
    entry = create_video_entry(field_grid, row, col)
    text_entries["Video"] = entry
    current_state = StateWrapper()
    states.append(current_state)
    create_image_wrapper(current_state, field_grid, row+1, 0)
    add_commands(text_entries, field_grid)
    row += 2
    global save_field_btn
    save_field_btn = tk.Button(
        field_grid, text="Save Fields",
        bg="#0078d7", fg="white", font=("Arial", 12, "bold"),
        command=lambda: save_field(text_entries, save_window)
    )
    save_field_btn.grid(row=row, column=0, pady=10, sticky="w")
def add_commands(text_entries, field_grid):

    for field, entry in text_entries.items():
        character='\n'
        if field=='Description':
            character='|||'
        print(f"Adding commands for {field} with character '{character}'")  # Debug print
        if entry is not None:
            entry.bind("<Return>", lambda e, en=entry,ch=character: on_modified(en, field_grid,text_entries,ch))
            entry.bind("<BackSpace>", lambda e, en=entry,ch=character: on_modified(en, field_grid,text_entries,ch))
            entry.bind("<Delete>", lambda e, en=entry,ch=character: on_modified(en, field_grid,text_entries,ch))
            entry.bind("<<Paste>>", lambda e, en=entry,ch=character: on_modified(en, field_grid,text_entries,ch))
            entry.bind("<<Cut>>", lambda e, en=entry,ch=character: on_modified(en, field_grid,text_entries,ch))