"""Fix remaining sheet issues."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from modules.sheet_client import SheetClient
from config.settings import CREDENTIALS_PATH, SHEET_NAME

sc = SheetClient(CREDENTIALS_PATH, SHEET_NAME)

# --- Fix 1: Delete duplicate SERP date column (col 7 = 2026-06-06_d) ---
print("=== Fix 1: Duplicate date column ===")
ws = sc.get_tab("SERP")
r1 = ws.row_values(1)
if len(r1) >= 7 and r1[6] == "2026-06-06_d":
    # Delete column G (7th column, 1-indexed)
    ws.delete_columns(7)
    print("Deleted duplicate date column G (2026-06-06_d)")
else:
    print("No duplicate column found")

# --- Fix 2: Delete duplicate row 4 (stale "seo agency mumbai" row) ---
print("\n=== Fix 2: Duplicate data row ===")
vals = ws.get_all_values()
if len(vals) >= 4:
    r3_kw = (vals[2][0] or "").strip()
    r3_tu = (vals[2][1] or "").strip()
    r4_kw = (vals[3][0] or "").strip()
    r4_tu = (vals[3][1] or "").strip()
    if (r3_kw == r4_kw and r3_tu == r4_tu):
        ws.delete_rows(4)
        print(f"Deleted duplicate row 4 ({r4_kw})")
    else:
        print(f"Rows 3/4 not duplicate: {r3_kw} vs {r4_kw}")
else:
    print("Not enough rows")

# --- Fix 3: Check Website Insights URL cell ---
print("\n=== Fix 3: Website Insights empty URL ===")
wi = sc.get_tab("Website Tracking & Insights")
vals3 = wi.get_all_values()
for i, r in enumerate(vals3, 1):
    url_cell = (r[0] or "").strip()
    print(f"  r{i}: URL={url_cell!r} rest={r[1:]}")
    if i == 3 and not url_cell:
        # Cell value at A3: might be a hyperlink issue
        # Write the URL explicitly
        wi.update_cell(3, 1, "https://digichefs.com/")
        print("  -> Updated A3 with explicit URL")

# --- Fix 4: Add "Search Intent" header to Keywords tab ---
print("\n=== Fix 4: Keywords tab header ===")
kw = sc.get_tab("Keywords")
kw_header = kw.row_values(1)
print(f"Keywords header: {kw_header}")
if len(kw_header) < 5:
    kw.update_cell(1, 5, "Search Intent")
    print("Added 'Search Intent' as 5th column header")
elif not kw_header[4]:
    kw.update_cell(1, 5, "Search Intent")
    print("Filled empty 5th column header with 'Search Intent'")
else:
    print(f"5th column header already: {kw_header[4]!r}")

# --- Verify all fixes ---
print("\n=== Verification ===")
serp = sc.get_tab("SERP")
s1 = serp.row_values(1)
print(f"SERP r1: {s1}")
print(f"SERP r3: {serp.row_values(3)[:2]}")
print(f"SERP r4: {serp.row_values(4)[:2]}")

wi2 = sc.get_tab("Website Tracking & Insights")
w3 = wi2.row_values(3)
print(f"Website r3: URL={w3[0]!r}")

kw2 = sc.get_tab("Keywords")
print(f"Keywords r1: {kw2.row_values(1)}")

print("\n✅ All fixes applied")
