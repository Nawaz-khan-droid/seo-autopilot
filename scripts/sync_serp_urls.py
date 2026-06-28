"""Update SERP tab rows to match new target URLs from cleanup."""
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
serp = sc.get_tab("SERP")
vals = serp.get_all_values()
header = vals[0]
print(f"SERP headers: {header}")

NEW_URL = "https://digichefs.com/seo-agency-mumbai/"
updates = 0
for i in range(2, len(vals)):
    row = vals[i]
    keyword = (row[0] or "").strip()
    old_url = (row[1] or "").strip()
    if old_url in ("https://digichefs.com/", "https://digichefs.com", "") and keyword:
        serp.update_cell(i + 1, 2, NEW_URL)
        print(f"  r{i+1}: {keyword!r}: {old_url} -> {NEW_URL}")
        updates += 1
        time.sleep(0.5)

if updates:
    print(f"Updated {updates} SERP row(s)")
else:
    print("No stale target URLs found in SERP tab")

# Verify
serp2 = sc.get_tab("SERP")
for r in serp2.get_all_values()[2:]:
    print(f"  {r[0]!r}: {r[1]!r}")
