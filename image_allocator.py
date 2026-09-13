"""
Smart Image Allocator for Facebook Marketplace Listings
======================================================
Provides intelligent image assignment from a bulk images folder:
1. STRICT ZERO-DUPLICATE PER ACCOUNT:
   An image is never assigned more than once to the same Facebook account (neither in the current batch nor historically in image_usage_log.json).
2. MAXIMUM TEMPORAL / SEQUENTIAL GAP:
   Images are reused across DIFFERENT accounts using a phased circular offset algorithm:
   Offset_k = floor(k * M / K)
   This spaces usage of the same image across different accounts by a large sequential gap (e.g., 25-50+ listings),
   drastically reducing the probability of concurrent uploads or pattern detection.
"""

import os
import re
import json
from typing import List, Dict, Any, Tuple, Optional


def natural_sort_key(s: str):
    """Sort filenames with numbers naturally (img1, img2, ..., img10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', os.path.basename(s))]


def get_valid_images_from_folder(folder_path: str) -> List[str]:
    """
    Recursively scans folder_path for image files (.jpg, .jpeg, .png, .webp, .bmp).
    Returns naturally sorted list of absolute paths.
    """
    if not folder_path or not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return []

    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    found = []

    # First collect files directly in the folder
    try:
        for entry in os.scandir(folder_path):
            if entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in valid_exts:
                    found.append(os.path.abspath(entry.path).replace("\\", "/"))
    except Exception:
        pass

    # Then collect files in subdirectories (recursive)
    try:
        for root, _, files in os.walk(folder_path):
            if os.path.abspath(root).replace("\\", "/") == os.path.abspath(folder_path).replace("\\", "/"):
                continue  # already scanned top level
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in valid_exts:
                    full_path = os.path.abspath(os.path.join(root, f)).replace("\\", "/")
                    if full_path not in found:
                        found.append(full_path)
    except Exception:
        pass

    # Deduplicate while preserving order, then natural sort
    unique_list = list(dict.fromkeys(found))
    unique_list.sort(key=natural_sort_key)
    return unique_list


def get_active_account_emails() -> List[str]:
    """Reads account emails from emails.csv if available."""
    emails = []
    csv_path = "emails.csv"
    if os.path.exists(csv_path):
        try:
            import pandas as pd
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            for _, row in df.iterrows():
                em = row.get("email", "").strip() or row.get("Email", "").strip()
                if em and em not in emails:
                    emails.append(em)
        except Exception:
            pass
    if not emails:
        emails = ["Account_1", "Account_2"]
    return emails


def allocate_images(
    pool: List[str],
    num_listings: int,
    accounts: Optional[List[str]] = None,
    images_per_listing: int = 1,
    min_gap: int = 25,
    usage_log: Optional[Dict[str, list]] = None
) -> Tuple[Dict[int, List[str]], Dict[str, Any]]:
    """
    Allocates images from pool across num_listings according to interleaved account distribution.

    Parameters:
      pool: list of image paths
      num_listings: number of listings to assign images to
      accounts: list of active accounts (e.g. ['id1@gmail.com', 'id2@gmail.com'])
      images_per_listing: number of images per listing (default 1)
      min_gap: desired minimum listing distance before reusing an image on a different account
      usage_log: {image_path: [accounts_that_already_used_it]}

    Returns:
      (assignments, meta)
      where assignments is {listing_index: [image_path_1, ...]}
    """
    if usage_log is None:
        try:
            from Open_fb import load_image_usage_log
            usage_log = load_image_usage_log()
        except Exception:
            usage_log = {}

    if not accounts:
        accounts = get_active_account_emails()

    k = len(accounts)
    m = len(pool)

    assignments: Dict[int, List[str]] = {i: [] for i in range(num_listings)}
    meta = {
        "pool_size": m,
        "total_listings": num_listings,
        "accounts": accounts,
        "unique_per_account": {acc: 0 for acc in accounts},
        "assigned_count": 0,
        "unassigned_count": 0,
        "reused_count": 0,
        "warnings": []
    }

    if m == 0 or num_listings == 0:
        meta["unassigned_count"] = num_listings
        if m == 0:
            meta["warnings"].append("No valid images found in the selected folder.")
        return assignments, meta

    # Track usage within this batch
    acc_used: Dict[str, set] = {acc: set() for acc in accounts}
    last_used_idx: Dict[str, int] = {}  # img -> global listing_index

    # Effective min_gap cannot exceed m // 2 or pool size
    effective_min_gap = min(min_gap, max(1, m // 2))

    for i in range(num_listings):
        acc = accounts[i % k]
        offset = (accounts.index(acc) * m) // k
        acc_listing_num = i // k

        needed = max(1, images_per_listing)
        chosen_for_this_listing = []

        for slot in range(needed):
            best_img = None
            best_gap = -1

            for step in range(m):
                cand = pool[(offset + acc_listing_num + slot + step) % m]

                # 1. Strict constraint: NEVER repeat on same ID in this batch
                if cand in acc_used[acc]:
                    continue

                # 2. Strict constraint: NEVER reuse an image already posted historically by this ID
                if acc in usage_log.get(cand, []):
                    continue

                # 3. Calculate sequential gap from previous assignment to another account
                gap = 999999 if cand not in last_used_idx else (i - last_used_idx[cand])

                if gap >= effective_min_gap:
                    best_img = cand
                    break
                elif gap > best_gap:
                    best_gap = gap
                    best_img = cand

            if best_img is not None:
                chosen_for_this_listing.append(best_img)
                acc_used[acc].add(best_img)
                if best_img in last_used_idx:
                    meta["reused_count"] += 1
                last_used_idx[best_img] = i

        assignments[i] = chosen_for_this_listing
        if chosen_for_this_listing:
            meta["assigned_count"] += 1
        else:
            meta["unassigned_count"] += 1

    for acc in accounts:
        meta["unique_per_account"][acc] = len(acc_used[acc])

    # Check if pool ran out for any account
    for idx, acc in enumerate(accounts):
        acc_listings_count = len([i for i in range(num_listings) if i % k == idx])
        needed_for_acc = acc_listings_count * images_per_listing
        actual_for_acc = len(acc_used[acc])
        if actual_for_acc < needed_for_acc:
            diff = needed_for_acc - actual_for_acc
            meta["warnings"].append(
                f"Image pool has {m} photos. Account '{acc}' was assigned {actual_for_acc} unique images ({diff} listings need additional images to avoid duplicates)."
            )

    return assignments, meta
