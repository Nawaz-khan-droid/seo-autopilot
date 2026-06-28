"""One-time migration: fix SERP tab schema to match spec."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from modules.sheet_client import SheetClient
from config.settings import CREDENTIALS_PATH, SHEET_NAME

sc = SheetClient(CREDENTIALS_PATH, SHEET_NAME)
ws = sc.get_tab("SERP")

# Step 1: Verify current header
header = ws.row_values(1)
print(f"Current row 1: {header}")

if len(header) < 5:
    print(f"ERROR: SERP tab has only {len(header)} columns, expected >= 5")
    sys.exit(1)

# Step 2: Rename "Avg Position" to "Search Intent" in cell E1
current_col5 = header[4].strip()
print(f"Current col 5 header: {current_col5!r}")

if current_col5 == "Search Intent":
    print("Already 'Search Intent' — no change needed")
elif current_col5 == "Avg Position":
    ws.update_cell(1, 5, "Search Intent")
    print("Renamed column 5 from 'Avg Position' to 'Search Intent'")
else:
    print(f"Unexpected column 5 header: {current_col5!r}. Renaming anyway.")
    ws.update_cell(1, 5, "Search Intent")

# Step 3: Normalise date row (row 2) to ISO format
# Current: ['', '', '', '', 'June', '-Jun-05', '-Jun-06', '-Jun-07', '2026-06-06']
# After:   ['', '', '', '', '',       '2026-06-05', '2026-06-06', '2026-06-07', '2026-06-06']
# But col 7 and col 9 would both become '2026-06-06' → duplicate!
# Fix: append '_o' suffix to the older duplicate (col 7 → '2026-06-06_o')

date_row = ws.row_values(2)
print(f"Date row (r2):  {date_row}")

from_date_map = {
    "-Jun-05": "2026-06-05",
    "-Jun-06": "2026-06-06",
    "-Jun-07": "2026-06-07",
}

updates = {}
for col_idx in range(5, len(date_row)):
    val = (date_row[col_idx] or "").strip()
    if val in from_date_map:
        new_val = from_date_map[val]
        updates[col_idx] = new_val
        print(f"  Cell (2, {col_idx + 1}): '{val}' -> '{new_val}'")

# Handle duplicate '2026-06-06' by renaming the FIRST occurrence to '_o'
seen = {}
for col_idx in sorted(updates.keys()):
    val = updates[col_idx]
    if val in seen:
        updates[col_idx] = val + "_o"
        print(f"  Cell (2, {col_idx + 1}): duplicate '{val}' -> '{val}_o'")
    seen[val] = col_idx

# If column 9 is '2026-06-06' and a normalised column also becomes '2026-06-06',
# the normalised one (earlier) gets the '_o' suffix
existing_iso = {}
for col_idx in range(5, len(date_row)):
    raw = (date_row[col_idx] or "").strip()
    if raw.startswith("2026-") and len(raw) == 10:
        existing_iso[col_idx] = raw

for col_idx, new_val in updates.items():
    if new_val.rstrip("_o") in existing_iso.values():
        # There's an existing ISO column with this date
        # Check if the existing one is a different column
        for existing_col, existing_date in existing_iso.items():
            if existing_date == new_val.rstrip("_o") and existing_col != col_idx:
                updates[col_idx] = new_val + "_d"
                print(f"  Cell (2, {col_idx + 1}): conflit with col {existing_col + 1} -> '{updates[col_idx]}'")
                break

# Apply updates
for col_idx, new_val in updates.items():
    if (date_row[col_idx] or "").strip() != new_val:
        ws.update_cell(2, col_idx + 1, new_val)

# Step 4: Clear the 'June' label in row 2, column 5
if (date_row[4] or "").strip() == "June":
    ws.update_cell(2, 5, "")
    print("  Cell (2, 5): cleared 'June' label")

# Step 5: Update row 1 date column headers (replace 'Rank, Rank, Rank, Rank' with dates)
header = ws.row_values(1)
new_header = list(header)
changed = False
for col_idx in range(5, len(header)):
    date_val = (ws.row_values(2)[col_idx] or "").strip() if col_idx < len(ws.row_values(2)) else ""
    if date_val and date_val.startswith("2026-"):
        if new_header[col_idx] != date_val:
            print(f"  Cell (1, {col_idx + 1}): '{new_header[col_idx]}' -> '{date_val}'")
            new_header[col_idx] = date_val
            changed = True

if changed:
    ws.update("A1:Z1", [new_header])
    
print("\nMigration complete. SERP tab is now compatible with new schema.")

# Verify
header_v = ws.row_values(1)
date_v = ws.row_values(2)
print(f"\nVerification:")
print(f"  Row 1: {header_v}")
print(f"  Row 2: {date_v}")
