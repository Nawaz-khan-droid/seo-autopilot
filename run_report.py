"""
Monthly SEO Report Generator — One-Command PDF Report from Google Sheets Data.

Usage:
    python run_report.py
    python run_report.py --month "June 2026"
    python run_report.py --agency "Your Agency" --client "Client Name"
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)

from config.settings import CREDENTIALS_PATH, SHEET_NAME, GROQ_API_KEY, GROQ_MODEL
from modules.sheet_client import SheetClient
from modules.groq_client import GroqClient
from report.generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate a monthly SEO report PDF")
    parser.add_argument("--agency", default="Your SEO Agency", help="Agency name for the report cover")
    parser.add_argument("--client", default="Client", help="Client name for the report")
    parser.add_argument("--month", default="", help="Report month (e.g. 'June 2026'). Auto-detected if empty.")
    parser.add_argument("--output", default="output", help="Output directory for reports")
    parser.add_argument("--format", default="pdf", choices=["pdf", "ppt"],
                        help="Output format: pdf or ppt (PowerPoint)")
    args = parser.parse_args()

    # Validate credentials
    creds = CREDENTIALS_PATH
    if not os.path.exists(creds):
        print(f"ERROR: Credentials file not found at '{creds}'")
        print("Set CREDENTIALS_PATH in .env or place credentials.json in the project root.")
        sys.exit(1)

    sheet = SheetClient(credentials_path=creds, sheet_name=SHEET_NAME)
    groq = GroqClient(api_key=GROQ_API_KEY, model=GROQ_MODEL)

    gen = ReportGenerator(
        sheet=sheet,
        groq_client=groq,
        agency_name=args.agency,
        client_name=args.client,
        output_dir=args.output,
    )

    fmt = "ppt" if args.format == "ppt" else "pdf"
    print(f"Generating {fmt.upper()} report for {args.client} ({args.month or 'current month'})...")
    filepath = gen.run(report_month=args.month or None, output_format=fmt)
    print(f"\nOK - Report generated: {filepath}")
    print(f"   Size: {os.path.getsize(filepath) // 1024} KB")


if __name__ == "__main__":
    main()
