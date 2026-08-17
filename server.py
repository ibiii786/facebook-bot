import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import subprocess
import ast
import shutil
import tkinter as tk
from tkinter import filedialog
import threading
import pandas as pd

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from save_state_screen import get_failed_fields, run_bot
from Open_fb import (
    main as run_fb_bot,
    distribute_among_accounts,
    get_live_bot_state
)
from renew import main as renew_main
from save_state_screen import main as save_state_main
from Assets.Files.SaveFiles.SaveFile import add_to_prev
import asyncio

app = FastAPI(title="Facebook Marketplace Bot Backend")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── Adapter Classes to Emulate Tkinter Control Interfaces ───────────────────
class SimpleGetter:
    def __init__(self, value: Any):
        self._value = value

    def get(self, *args, **kwargs) -> Any:
        return self._value


class TextGetter:
    def __init__(self, value: str):
        self._value = value

    def get(self, index1="1.0", index2="end") -> str:
        return str(self._value)


class EntryAdapter:
    """
    Emulates the entry tuple structure returned by Tkinter UI:
    (img_entries, title_entry, description_entry, category_entry, location_entry,
     tags_entry, price_entry, condition_entry, availability_entry, video_entry, wrapper, opt_vars)
    """
    def __init__(self, data: dict):
        images = data.get("images", [])
        if not isinstance(images, list):
            images = [images] if images else []

        self.img_entries = [SimpleGetter(str(img)) for img in images]
        self.title_entry = SimpleGetter(str(data.get("title", "")))
        self.description_entry = TextGetter(str(data.get("description", "")))
        self.category_entry = SimpleGetter(str(data.get("category", "")))
        self.location_entry = SimpleGetter(str(data.get("location", "")))
        
        tags = data.get("tags", [])
        if isinstance(tags, list):
            tags_str = ",".join(str(t) for t in tags)
        else:
            tags_str = str(tags)
        self.tags_entry = SimpleGetter(tags_str)

        self.price_entry = SimpleGetter(str(data.get("price", "0")))
        self.condition_entry = SimpleGetter(str(data.get("condition", "")))
        self.availability_entry = SimpleGetter(str(data.get("availability", "")))
        self.video_entry = SimpleGetter(str(data.get("video", "")))
        self.wrapper = None
        self.opt_vars = [
            SimpleGetter(int(data.get("public_meetup", 0))),
            SimpleGetter(int(data.get("door_pickup", 0))),
            SimpleGetter(int(data.get("door_dropoff", 0))),
        ]

    def __getitem__(self, idx: int):
        items = [
            self.img_entries,
            self.title_entry,
            self.description_entry,
            self.category_entry,
            self.location_entry,
            self.tags_entry,
            self.price_entry,
            self.condition_entry,
            self.availability_entry,
            self.video_entry,
            self.wrapper,
            self.opt_vars,
        ]
        return items[idx]


# ── Pydantic Request Models ────────────────────────────────────────────────
class ListingItem(BaseModel):
    images: List[str] = []
    video: Optional[str] = ""
    title: str = ""
    category: str = ""
    price: Any = "0"
    location: str = ""
    condition: str = ""
    availability: str = ""
    tags: List[str] = []
    description: str = ""
    public_meetup: int = 0
    door_pickup: int = 0
    door_dropoff: int = 0


class BotRunRequest(BaseModel):
    listings: List[ListingItem]
    wait_time: int = 2
    wait_time_accounts: int = 2
    marketplace: str = "UK"
    wait_for_review: bool = False
    max_concurrent_browsers: int = 2
    review_timeout_mins: int = 30


class CountRequest(BaseModel):
    count: int = 2


class SavePresetRequest(BaseModel):
    name: str
    fields: List[Dict[str, Any]]


class SaveSessionRequest(BaseModel):
    state: Dict[str, Any]


SESSION_FILE = os.path.join(os.path.dirname(__file__), "session_state.json")


@app.post("/save-session")
def api_save_session(req: SaveSessionRequest):
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(req.state, f, indent=2)
        return {"status": "success", "message": "Session saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/load-session")
def api_load_session():
    if os.path.exists(SESSION_FILE) and os.path.getsize(SESSION_FILE) > 0:
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"status": "success", "state": data}
        except Exception as e:
            return {"status": "success", "state": None}
    return {"status": "success", "state": None}


# ── Task Execution Handlers ─────────────────────────────────────────────────
def run_bot_task(
    entries_data: List[dict],
    wait_time: int,
    wait_time_accounts: int,
    marketplace: str,
    wait_for_review: bool,
    max_concurrent_browsers: int,
    review_timeout_mins: int,
    stop_event: threading.Event
):
    adapted_entries = [EntryAdapter(item) for item in entries_data]
    run_fb_bot(
        adapted_entries,
        time_sleep=wait_time,
        wait_time_accounts=wait_time_accounts,
        marketplace_location=marketplace,
        wait_for_review=wait_for_review,
        stop_event=stop_event,
        max_concurrent_browsers=max_concurrent_browsers
    )


def run_distribute_task(
    entries_data: List[dict],
    wait_time: int,
    wait_time_accounts: int,
    marketplace: str,
    wait_for_review: bool,
    max_concurrent_browsers: int,
    review_timeout_mins: int,
    stop_event: threading.Event
):
    adapted_entries = [EntryAdapter(item) for item in entries_data]
    distribute_among_accounts(
        adapted_entries,
        time_sleep=wait_time,
        wait_time_accounts=wait_time_accounts,
        marketplace_location=marketplace,
        wait_for_review=wait_for_review,
        stop_event=stop_event,
        max_concurrent_browsers=max_concurrent_browsers
    )


# ── Endpoints ───────────────────────────────────────────────────────────────
import math

def clean_nan(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj

@app.post('/getfailedfields')
def get_failed_fields_endpoint():
    try:
        failed_fields = get_failed_fields()
        failed_fields = clean_nan(failed_fields)
        return {"status": "success", "failed_fields": failed_fields}
    except Exception as e:
        return {"status": "error", "message": str(e)}

current_background_tasks: list[threading.Thread] = []
stop_event = threading.Event()

@app.get("/bot-status")
def api_bot_status():
    """Returns real-time status of all active account workers and queue metrics."""
    return get_live_bot_state()

@app.post("/run-bot")
def api_run_bot(req: BotRunRequest):
    entries_data = [item.dict() for item in req.listings]
    global current_background_tasks, stop_event
    stop_event.clear()

    t = threading.Thread(
        target=run_bot_task,
        args=(
            entries_data,
            req.wait_time,
            req.wait_time_accounts,
            req.marketplace,
            req.wait_for_review,
            req.max_concurrent_browsers,
            req.review_timeout_mins,
            stop_event
        ),
        daemon=True,
    )
    current_background_tasks.append(t)
    t.start()
    return {"status": "started", "message": "Bot execution started in background."}

@app.post("/distribute-bot")
def api_distribute_bot(req: BotRunRequest):
    entries_data = [item.dict() for item in req.listings]
    global current_background_tasks, stop_event
    stop_event.clear()

    t = threading.Thread(
        target=run_distribute_task,
        args=(
            entries_data,
            req.wait_time,
            req.wait_time_accounts,
            req.marketplace,
            req.wait_for_review,
            req.max_concurrent_browsers,
            req.review_timeout_mins,
            stop_event
        ),
        daemon=True,
    )
    current_background_tasks.append(t)
    t.start()
    return {"status": "started", "message": "Distribution bot execution started in background."}

@app.post("/end-tasks")
def end_tasks():
    global current_background_tasks, stop_event
    stop_event.set()
    current_background_tasks = []
    return {"status": "success", "message": "Stop signal sent."}



@app.post("/renew")
def api_renew(req: CountRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(renew_main, req.count, "renew")
    return {"status": "started", "message": f"Renew listings ({req.count}) started in background."}


@app.post("/delete-relist")
def api_delete_relist(req: CountRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(renew_main, req.count, "relist")
    return {"status": "started", "message": f"Delete & relist ({req.count}) started in background."}


@app.post("/run-failed")
def api_run_failed(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_bot)
    return {"status": "started", "message": "Regenerating failed listings started in background."}


class AccountProfile(BaseModel):
    email: str
    phone: Optional[str] = ""
    password: Optional[str] = ""
    proxy: Optional[str] = ""


class LoginSessionRequest(BaseModel):
    email: str
    password: Optional[str] = ""
    proxy: Optional[str] = ""


@app.get("/accounts")
def get_accounts():
    from login_profile import load_emails_df, is_account_authenticated
    df = load_emails_df()
    accounts = []
    for row in df.to_dict(orient="records"):
        email = row.get("email", "")
        phone = row.get("phone", "")
        row["authenticated"] = is_account_authenticated(email, phone)
        accounts.append(row)
    return {"accounts": accounts}


@app.post("/accounts")
def save_account(acc: AccountProfile):
    from login_profile import load_emails_df, email_to_safe
    df = load_emails_df()
    email_val = acc.email.strip()
    if not email_val:
        raise HTTPException(status_code=400, detail="Email is required.")
    
    phone_val = acc.phone.strip() if acc.phone else ""
    pass_val = acc.password.strip() if acc.password else ""
    proxy_val = acc.proxy.strip() if acc.proxy else ""

    if email_val in df['email'].values:
        df.loc[df['email'] == email_val, 'phone'] = phone_val
        df.loc[df['email'] == email_val, 'password'] = pass_val
        df.loc[df['email'] == email_val, 'proxy'] = proxy_val
    else:
        new_row = {'email': email_val, 'phone': phone_val, 'password': pass_val, 'proxy': proxy_val}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv('emails.csv', index=False)
    safe_email = email_to_safe(email_val, phone_val)
    from pathlib import Path
    profile_dir = Path("profiles") / safe_email
    profile_dir.mkdir(parents=True, exist_ok=True)
    return {"status": "success", "message": f"Account '{email_val}' saved."}


@app.post("/login-session")
def api_login_session(req: LoginSessionRequest, background_tasks: BackgroundTasks):
    from login_profile import auto_login_session
    background_tasks.add_task(auto_login_session, req.email, req.password or "", req.proxy or "")
    return {"status": "started", "message": f"Auto-login session started for '{req.email}'."}


@app.delete("/accounts")
def delete_account(email: str = Query(...)):
    from login_profile import load_emails_df, email_to_safe
    df = load_emails_df()
    if email not in df['email'].values:
        raise HTTPException(status_code=404, detail="Account not found.")
    
    phone_row = df.loc[df['email'] == email, 'phone'].values
    phone_val = phone_row[0] if len(phone_row) > 0 else ""

    df = df[df['email'] != email].reset_index(drop=True)
    df.to_csv('emails.csv', index=False)

    from pathlib import Path
    profile_dir = Path("profiles") / email_to_safe(email, phone_val)
    if profile_dir.exists():
        try:
            shutil.rmtree(profile_dir)
        except Exception:
            pass
    return {"status": "success", "message": f"Account '{email}' deleted."}


@app.get("/saved-states")
def api_saved_states():
    dir_path = "./saved_states"
    if not os.path.exists(dir_path):
        return {"states": []}
    files = [f[:-4] for f in os.listdir(dir_path) if f.endswith(".csv")]
    return {"states": files}


@app.post("/save-fields")
def api_save_fields(req: SavePresetRequest):
    df_rows = []
    for f in req.fields:
        images = f.get("images", [])
        tags = f.get("tags", [])
        df_rows.append({
            "Images": images if isinstance(images, list) else [images],
            "Title": f.get("title", ""),
            "Description": f.get("description", ""),
            "Category": f.get("category", ""),
            "Location": f.get("location", ""),
            "Tags": tags if isinstance(tags, list) else [tags],
            "Price": f.get("price", "0"),
            "Condition": f.get("condition", ""),
            "Availability": f.get("availability", ""),
            "Video": f.get("video", ""),
            "Public meetup": f.get("public_meetup", 0),
            "Door pickup": f.get("door_pickup", 0),
            "Door dropoff": f.get("door_dropoff", 0),
        })

    df = pd.DataFrame(df_rows)
    add_to_prev(df, req.name)
    return {"status": "success", "message": f"Preset '{req.name}' saved successfully."}


# ── Bulk Import/Export & Folder Auto-Gen Endpoints ─────────────────────────

class ScanFolderRequest(BaseModel):
    folder_path: str


@app.post("/import-csv")
async def api_import_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        filename = file.filename.lower()
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            import io
            df = pd.read_excel(io.BytesIO(contents))
        else:
            import io
            df = pd.read_csv(io.BytesIO(contents))

        fields = []
        for _, row in df.iterrows():
            raw_imgs = str(row.get("Images", row.get("images", "")))
            if raw_imgs.startswith("[") and raw_imgs.endswith("]"):
                try:
                    imgs = ast.literal_eval(raw_imgs)
                except Exception:
                    imgs = [s.strip() for s in raw_imgs.strip("[]").split(",") if s.strip()]
            else:
                imgs = [s.strip() for s in raw_imgs.split("|") if s.strip()] or [s.strip() for s in raw_imgs.split(",") if s.strip()]

            raw_tags = str(row.get("Tags", row.get("tags", "")))
            if raw_tags.startswith("[") and raw_tags.endswith("]"):
                try:
                    tags = ast.literal_eval(raw_tags)
                except Exception:
                    tags = [s.strip() for s in raw_tags.strip("[]").split(",") if s.strip()]
            else:
                tags = [s.strip() for s in raw_tags.split(",") if s.strip()]

            fields.append({
                "title": str(row.get("Title", row.get("title", ""))),
                "description": str(row.get("Description", row.get("description", ""))),
                "category": str(row.get("Category", row.get("category", "Furniture"))),
                "price": str(row.get("Price", row.get("price", "85"))),
                "location": str(row.get("Location", row.get("location", ""))),
                "condition": str(row.get("Condition", row.get("condition", "New"))),
                "availability": str(row.get("Availability", row.get("availability", "List as In Stock"))),
                "tags": tags,
                "images": imgs,
                "video": str(row.get("Video", row.get("video", ""))),
                "public_meetup": 1 if str(row.get("Public meetup", row.get("public_meetup", "0"))) in ["1", "True", "true"] else 0,
                "door_pickup": 1 if str(row.get("Door pickup", row.get("door_pickup", "0"))) in ["1", "True", "true"] else 0,
                "door_dropoff": 1 if str(row.get("Door dropoff", row.get("door_dropoff", "1"))) in ["1", "True", "true"] else 0,
            })
        return {"status": "success", "count": len(fields), "fields": fields}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV/Excel parse failed: {str(e)}")


@app.get("/download-template")
def api_download_template():
    template_path = os.path.join(os.path.dirname(__file__), "sample_listings_template.csv")
    if not os.path.exists(template_path):
        sample_df = pd.DataFrame([
            {
                "Title": "Modern Velvet Sofa",
                "Category": "Furniture",
                "Price": "95",
                "Location": "London",
                "Condition": "New",
                "Availability": "List as In Stock",
                "Tags": "sofa, couch, furniture, living room",
                "Description": "Brand new high quality 3-seater sofa. Fast delivery available!",
                "Images": "C:/Images/sofa1.jpg|C:/Images/sofa2.jpg",
                "Video": "",
                "Public meetup": 0,
                "Door pickup": 0,
                "Door dropoff": 1
            },
            {
                "Title": "Solid Wood Dining Table",
                "Category": "Furniture",
                "Price": "120",
                "Location": "Manchester",
                "Condition": "New",
                "Availability": "List as In Stock",
                "Tags": "table, dining, wood, home",
                "Description": "Beautiful solid oak dining table. Seats 6 comfortably.",
                "Images": "C:/Images/table1.jpg",
                "Video": "",
                "Public meetup": 0,
                "Door pickup": 0,
                "Door dropoff": 1
            }
        ])
        sample_df.to_csv(template_path, index=False)
    return FileResponse(template_path, filename="sample_listings_template.csv", media_type="text/csv")


@app.post("/scan-folder")
def api_scan_folder(req: ScanFolderRequest):
    folder = req.folder_path.strip()
    if not os.path.exists(folder) or not os.path.isdir(folder):
        raise HTTPException(status_code=404, detail="Directory not found or invalid.")

    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    subdirs = [os.path.join(folder, d) for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))]

    items = []
    if subdirs:
        for sub in subdirs:
            folder_name = os.path.basename(sub).replace("_", " ").title()
            imgs = [os.path.abspath(os.path.join(sub, f)) for f in os.listdir(sub) if os.path.splitext(f)[1].lower() in valid_exts]
            if imgs:
                items.append({
                    "title": folder_name,
                    "category": "Furniture",
                    "price": "85",
                    "location": "",
                    "condition": "New",
                    "availability": "List as In Stock",
                    "tags": [t.lower() for t in folder_name.split() if len(t) > 2],
                    "description": f"High quality {folder_name}. Brand new in packaging. Fast local delivery available!",
                    "images": imgs,
                    "video": "",
                    "public_meetup": 0,
                    "door_pickup": 0,
                    "door_dropoff": 1
                })
    else:
        imgs = [os.path.abspath(os.path.join(folder, f)) for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in valid_exts]
        if imgs:
            items.append({
                "title": os.path.basename(folder).replace("_", " ").title(),
                "category": "Furniture",
                "price": "85",
                "location": "",
                "condition": "New",
                "availability": "List as In Stock",
                "tags": ["furniture", "home"],
                "description": "Brand new item available for order.",
                "images": imgs,
                "video": "",
                "public_meetup": 0,
                "door_pickup": 0,
                "door_dropoff": 1
            })

    return {"status": "success", "count": len(items), "fields": items}


@app.get("/load-fields")
def api_load_fields(name: str = Query(...)):
    filename = f"./saved_states/{name}.csv"
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="Preset file not found.")

    df = pd.read_csv(filename)
    for col in ["Images", "Tags"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else (x if isinstance(x, list) else []))

    if "Video" not in df.columns:
        df["Video"] = ""
    else:
        df["Video"] = df["Video"].fillna("")

    fields = []
    for _, row in df.iterrows():
        fields.append({
            "images": row["Images"] if isinstance(row["Images"], list) else [],
            "title": str(row.get("Title", "")),
            "description": str(row.get("Description", "")),
            "category": str(row.get("Category", "")),
            "location": str(row.get("Location", "")),
            "tags": row["Tags"] if isinstance(row["Tags"], list) else [],
            "price": row.get("Price", "0"),
            "condition": str(row.get("Condition", "")),
            "availability": str(row.get("Availability", "")),
            "video": str(row.get("Video", "")),
            "public_meetup": int(row.get("Public meetup", 0)) if not pd.isna(row.get("Public meetup")) else 0,
            "door_pickup": int(row.get("Door pickup", 0)) if not pd.isna(row.get("Door pickup")) else 0,
            "door_dropoff": int(row.get("Door dropoff", 0)) if not pd.isna(row.get("Door dropoff")) else 0,
        })

    return {"fields": fields}


# ── Native OS File Dialog Helper & Browsing Endpoints ──────────────────────
def open_native_file_dialog(dialog_type: str = "files") -> List[str]:
    """Open native OS file dialog. Works when server is started interactively."""
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        root.lift()
        root.focus_force()
        root.update()
        if dialog_type == "files":
            files = filedialog.askopenfilenames(
                parent=root,
                title="Select Image Files",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"), ("All Files", "*.*")]
            )
            root.destroy()
            return list(files) if files else []
        elif dialog_type == "video":
            file_path = filedialog.askopenfilename(
                parent=root,
                title="Select Video File",
                filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv *.webm"), ("All Files", "*.*")]
            )
            root.destroy()
            return [file_path] if file_path else []
        elif dialog_type == "folder":
            folder = filedialog.askdirectory(parent=root, title="Select Folder")
            root.destroy()
            return [folder] if folder else []
        else:
            root.destroy()
            return []
    except Exception as e:
        print(f"File dialog error: {e}")
        return []


@app.get("/browse-files")
def api_browse_files():
    paths = open_native_file_dialog("files")
    return {"paths": paths}


@app.get("/browse-video")
def api_browse_video():
    paths = open_native_file_dialog("video")
    return {"path": paths[0] if paths else ""}


@app.get("/browse-folder")
def api_browse_folder():
    paths = open_native_file_dialog("folder")
    return {"path": paths[0] if paths else ""}


@app.post("/upload-file")
async def api_upload_file(file: UploadFile = File(...)):
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"path": os.path.abspath(file_path)}


@app.get("/media-preview")
def api_media_preview(path: str = Query(...)):
    if os.path.exists(path) and os.path.isfile(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="File not found")


# ── Serve Static Web Frontend ───────────────────────────────────────────────
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    def read_index():
        return FileResponse(os.path.join(web_dir, "index.html"))

    @app.get("/{file_name}")
    def read_static_file(file_name: str):
        file_path = os.path.join(web_dir, file_name)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            if file_name.endswith('.css'):
                return FileResponse(file_path, media_type="text/css")
            if file_name.endswith('.js'):
                return FileResponse(file_path, media_type="application/javascript")
            return FileResponse(file_path)
        return FileResponse(os.path.join(web_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
