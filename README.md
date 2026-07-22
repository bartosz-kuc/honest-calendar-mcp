# honest-calendar-mcp

Local Google Calendar MCP server. Your calendar data never leaves your machine except to Google. No third party in the middle.

Companion project to [honest-gmail-mcp](https://github.com/bartosz-kuc/honest-gmail-mcp).

## Why

Most Calendar integrations for AI assistants route your event data through a hosted service that sees everything: meetings, attendees, locations, private descriptions. This one doesn't.

**Data flow:** `You ↔ this server (on your Mac) ↔ Google Calendar API`. That's it.

**You can read the entire server** — one file, ~250 lines of Python — and confirm exactly what it can and cannot do.

## Features

Six tools exposed over MCP:

- `list_calendars` — all calendars available on this account
- `list_events` — events in a calendar within a time range, with optional free-text search
- `get_event` — full details of a single event
- `create_event` — new event (timed or all-day), with attendees, description, location, timezone
- `update_event` — partial patch of an existing event
- `delete_event` — delete an event

All tools that send invites accept a `send_updates` parameter (`none` by default — no email is sent unless you explicitly ask for it).

## Requirements

- Python 3.10+
- A Google account you want to give it access to
- A one-time setup in Google Cloud Console (~10 min, can reuse the OAuth client from honest-gmail-mcp if you already set that up)

## Setup

### 1. Clone + install

```bash
git clone https://github.com/bartosz-kuc/honest-calendar-mcp.git
cd honest-calendar-mcp
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 2. Get Google OAuth credentials

Same process as honest-gmail-mcp — a Desktop-app OAuth client from your own Google Cloud project. If you already have a project set up, just enable the Calendar API on it:

1. https://console.cloud.google.com/ (signed in with the account you want to authorize)
2. Select existing project (or create new one)
3. **APIs & Services → Library** → search **Google Calendar API** → **Enable**
4. Reuse existing OAuth consent screen / client, OR create new — Desktop app type
5. Save `credentials.json` in this repo's root directory

### 3. First run (does the OAuth dance)

```bash
./venv/bin/python server.py
```

Browser opens → sign in → **Allow**. Token saved locally as `token.json`. Press Ctrl+C after.

### 4. Register with your MCP client

**Claude Code:**

```bash
claude mcp add calendar-personal /absolute/path/to/venv/bin/python /absolute/path/to/server.py
```

**Claude Desktop:** edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "calendar-personal": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

## Example usage

> "What's on my calendar tomorrow?"

AI calls `list_events` with tomorrow's time range → gets back events with summary, start, end, attendees.

> "Book a 1h call with alice@example.com next Thursday at 15:00."

AI calls `create_event` with summary, start, end, attendees, `send_updates: "all"` if you want Alice invited.

## Data flow (detail)

```
Your AI client (Claude Code / Claude Desktop)
         ↕  MCP protocol over stdio (local process pipe)
This server (Python, on your machine)
         ↕  HTTPS to googleapis.com
Google Calendar API
```

No cloud middle. No telemetry. `credentials.json` and `token.json` stay on your disk and are `.gitignore`d.

## Security notes

- **You own the OAuth client.** Nobody else can revoke, rotate, or misuse it.
- **Revoke anytime** at https://myaccount.google.com/permissions.
- **Scope requested:** `calendar` (full read/write on all your calendars). Google does not offer read-only + write-only splits for the standard Calendar scope; the write-heavy nature of a calendar-editing tool needs full scope.
- **No secrets in git.** `.gitignore` blocks `credentials.json`, `token.json`, and virtualenvs.
- **send_updates defaults to "none"** — the AI cannot accidentally spam attendees. You must explicitly ask for updates to be sent.

## Author

**Bartosz Kuć** — Warsaw-based developer, JDG owner running skanfirmy.pl.

- Site: https://skanfirmy.pl
- GitHub: https://github.com/bartosz-kuc

## License

MIT — see [LICENSE](LICENSE).
