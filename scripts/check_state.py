"""Check sheet state with retry logic."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from modules.sheet_client import SheetClient
from config.settings import CREDENTIALS_PATH, SHEET_NAME

sc = SheetClient(CREDENTIALS_PATH, SHEET_NAME)

for tab in ["AI Analysis", "SERP", "SERP History", "SERP Snapshot", "Competitor Snapshot", "Website Tracking & Insights"]:
    try:
        for attempt in range(3):
            try:
                ws = sc.get_tab(tab)
                vals = ws.get_all_values()
                print(f"\n=== {tab} ({len(vals)} rows) ===")
                for i, r in enumerate(vals[:5], 1):
                    print(f"  r{i}: {r}")
                if len(vals) > 5:
                    print(f"  ... +{len(vals)-5} more rows")
                break
            except Exception as e:
                print(f"  attempt {attempt+1} failed: {e}", file=sys.stderr)
                time.sleep(5)
        else:
            print(f"  FAILED after 3 attempts for {tab}")
    except Exception as e:
        print(f"  CRITICAL: {e}")
