#!/usr/bin/env python
"""One-shot OAuth authorizer for honest-calendar-mcp (multi-account).

Opens a browser, you pick the Google account and grant Calendar access, and the
refresh token is written to CALENDAR_TOKEN_PATH (default: token.json next to
this file). Reuses the same OAuth client as the rest of the honest-mcp family.

Usage (authorize a second account, e.g. kucio012):

    cd /Users/bartoszkuc/calendar-mcp
    CALENDAR_TOKEN_PATH="$PWD/token.kucio012.json" ./venv/bin/python authorize.py

Then sign in as the desired account in the browser window and click Allow.
"""

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
HERE = Path(__file__).parent
CRED_PATH = Path(os.environ.get("CALENDAR_CREDENTIALS_PATH", str(HERE / "credentials.json")))
TOKEN_PATH = Path(os.environ.get("CALENDAR_TOKEN_PATH", str(HERE / "token.json")))


def main() -> None:
    if not CRED_PATH.exists():
        raise SystemExit(f"Missing OAuth client file: {CRED_PATH}")
    print(f"Authorizing Calendar access -> writing token to: {TOKEN_PATH}")
    print("A browser window will open. Pick the Google account you want and click Allow.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CRED_PATH), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    TOKEN_PATH.write_text(creds.to_json())
    try:
        TOKEN_PATH.chmod(0o600)
    except OSError:
        pass
    print(f"OK: token written to {TOKEN_PATH}")


if __name__ == "__main__":
    main()
