"""One-time cleanup: fix keywords, delete stray column."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from modules.sheet_client import SheetClient
from config.settings import CREDENTIALS_PATH, SHEET_NAME

sc = SheetClient(CREDENTIALS_PATH, SHEET_NAME)

# --- Fix 1: Update homepage-targeted keywords to /seo-agency-mumbai/ ---
print("=== Fix 1: Keywords tab — homepage URLs -> /seo-agency-mumbai/ ===")
kw = sc.get_tab("Keywords")
records = kw.get_all_values()
header = records[0]
print(f"Header: {header}")

updates = 0
for i in range(1, len(records)):
    row = records[i]
    if len(row) < 2:
        continue
    keyword = (row[0] or "").strip()
    target_url = (row[1] or "").strip()
    if target_url in ("https://digichefs.com/", "https://digichefs.com", "digichefs.com/"):
        new_url = "https://digichefs.com/seo-agency-mumbai/"
        kw.update_cell(i + 1, 2, new_url)
        print(f"  r{i+1}: {keyword!r}: {target_url} -> {new_url}")
        updates += 1
        time.sleep(0.5)

if updates == 0:
    print("  No homepage-targeted keywords found")
else:
    print(f"  Updated {updates} keyword(s)")

# --- Fix 2: Delete 2026-06-07 column from SERP tab ---
print("\n=== Fix 2: SERP tab — delete stray '2026-06-07' column ===")
serp = sc.get_tab("SERP")
r1 = serp.row_values(1)
print(f"SERP headers: {r1}")

# Find 2026-06-07 column index (1-based)
col_idx = None
for i, h in enumerate(r1, start=1):
    if h == "2026-06-07":
        col_idx = i
        break

if col_idx:
    serp.delete_columns(col_idx)
    print(f"  Deleted column {col_idx} ('2026-06-07')")
else:
    print("  No '2026-06-07' column found")

# --- Fix 3: Verify ---
print("\n=== Verification ===")
kw2 = sc.get_tab("Keywords")
print("Keywords tab:")
for r in kw2.get_all_values():
    print(f"  {r}")

serp2 = sc.get_tab("SERP")
print(f"\nSERP tab headers: {serp2.row_values(1)}")

print("\nDone.")
