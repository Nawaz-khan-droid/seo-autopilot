"""Rotate Google service account key and update credentials.json.

Usage:
    python scripts/rotate_service_account.py [--project PROJECT_ID] [--key-id KEY_ID]

If --project and --key-id are provided, attempts to create a new key via the
IAM API and write it to secrets/credentials.json. Otherwise prints manual
rotation instructions.

Requires:
    pip install google-cloud-iam
    GOOGLE_APPLICATION_CREDENTIALS pointing to a key with iam.serviceAccountKeys.create
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SECRETS_DIR = Path(__file__).resolve().parent.parent / "secrets"
CREDS_PATH = SECRETS_DIR / "credentials.json"


def manual_instructions():
    print("=" * 60)
    print("MANUAL KEY ROTATION (no GCP IAM credentials available)")
    print("=" * 60)
    print()
    print("1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts")
    print("2. Select project: genaiapac-492516")
    print("3. Find service account: seo-automation-demo")
    print("4. Click the service account → Keys → Add Key → Create New Key")
    print("5. Choose JSON format → Download")
    print("6. Replace the file at: secrets/credentials.json")
    print("7. Delete the old key from the service account")
    print()
    print("After rotation:")
    print("  - Update GSC property access for the new service account email")
    print("  - Update GA4 property access if applicable")
    print("  - Re-verify Sheet access")
    print("=" * 60)


def auto_rotate(project_id: str, key_id: str):
    try:
        from google.cloud import iam_admin_v1
        from google.cloud.iam_admin_v1 import types
    except ImportError:
        logger.error("google-cloud-iam not installed. Run: pip install google-cloud-iam")
        manual_instructions()
        return

    client = iam_admin_v1.IAMClient()
    name = f"projects/{project_id}/serviceAccounts/seo-automation-demo@{project_id}.iam.gserviceaccount.com"

    if key_id:
        logger.info("Deleting old key %s ...", key_id)
        request = types.DeleteServiceAccountKeyRequest(
            name=f"{name}/keys/{key_id}"
        )
        client.delete_service_account_key(request=request)
        logger.info("Old key deleted.")

    logger.info("Creating new key ...")
    request = types.CreateServiceAccountKeyRequest(
        name=name,
        private_key_type=types.ServiceAccountPrivateKeyType.TYPE_GOOGLE_CREDENTIALS_FILE,
    )
    response = client.create_service_account_key(request=request)
    key_data = json.loads(response.private_key_data)

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    CREDS_PATH.write_text(json.dumps(key_data, indent=2), encoding="utf-8")
    logger.info("New key written to %s", CREDS_PATH)
    print()
    print("IMPORTANT: The old key has been deleted. Verify the new key works by running:")
    print("  python -c \"from modules.sheet_client import SheetClient; print('OK')\"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate Google SA key")
    parser.add_argument("--project", default="genaiapac-492516", help="GCP project ID")
    parser.add_argument("--key-id", default="", help="Existing key ID to delete (optional)")
    args = parser.parse_args()

    if args.key_id:
        auto_rotate(args.project, args.key_id)
    else:
        manual_instructions()
