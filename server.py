"""honest-calendar-mcp — minimal Google Calendar MCP server.

Exposes 6 tools over MCP stdio: list_calendars, list_events, get_event,
create_event, update_event, delete_event. Refresh token stored locally in
token.json next to this file. Same trust model as honest-gmail-mcp — data
flows only between your machine and Google.

Author: Bartosz Kuć <firma@bartosza.pl>
Repo:   https://github.com/bartosz-kuc/honest-calendar-mcp
License: MIT
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SCOPES = ["https://www.googleapis.com/auth/calendar"]

HERE = Path(__file__).parent
CRED_PATH = HERE / "credentials.json"
TOKEN_PATH = HERE / "token.json"


def get_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CRED_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


server = Server("calendar-personal")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_calendars",
            description="List all calendars available on this account with id, summary, and access role.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_events",
            description=(
                "List events in a calendar within a time range. Returns event id, summary, start, end, "
                "location, attendees. Default calendar is 'primary'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "default": "primary"},
                    "time_min": {"type": "string", "description": "RFC3339 (e.g. 2026-07-22T00:00:00+02:00)"},
                    "time_max": {"type": "string", "description": "RFC3339"},
                    "max_results": {"type": "integer", "default": 50, "maximum": 250},
                    "query": {"type": "string", "description": "Free-text search filter"},
                },
                "required": ["time_min", "time_max"],
            },
        ),
        Tool(
            name="get_event",
            description="Fetch full details of a single event by id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "default": "primary"},
                    "event_id": {"type": "string"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="create_event",
            description=(
                "Create a new event. Times as RFC3339 datetimes (timed) or YYYY-MM-DD (all-day). "
                "Attendees is a list of email strings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "default": "primary"},
                    "summary": {"type": "string"},
                    "start": {"type": "string", "description": "RFC3339 datetime or YYYY-MM-DD for all-day"},
                    "end": {"type": "string", "description": "RFC3339 datetime or YYYY-MM-DD for all-day"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                    "timezone": {"type": "string", "description": "IANA tz like Europe/Warsaw, default Europe/Warsaw"},
                    "send_updates": {"type": "string", "enum": ["all", "externalOnly", "none"], "default": "none"},
                },
                "required": ["summary", "start", "end"],
            },
        ),
        Tool(
            name="update_event",
            description=(
                "Partial update of an existing event. Only pass the fields you want to change. "
                "Uses PATCH semantics."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "default": "primary"},
                    "event_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                    "timezone": {"type": "string"},
                    "send_updates": {"type": "string", "enum": ["all", "externalOnly", "none"], "default": "none"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="delete_event",
            description="Delete an event by id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "default": "primary"},
                    "event_id": {"type": "string"},
                    "send_updates": {"type": "string", "enum": ["all", "externalOnly", "none"], "default": "none"},
                },
                "required": ["event_id"],
            },
        ),
    ]


def _time_field(iso: str, tz: str) -> dict:
    # All-day events use "date": "YYYY-MM-DD"; timed events use "dateTime": full RFC3339.
    if len(iso) == 10 and iso.count("-") == 2:
        return {"date": iso}
    return {"dateTime": iso, "timeZone": tz}


def _build_event_body(args: dict, tz_default: str) -> dict:
    tz = args.get("timezone") or tz_default
    body: dict = {}
    if "summary" in args:
        body["summary"] = args["summary"]
    if "description" in args:
        body["description"] = args["description"]
    if "location" in args:
        body["location"] = args["location"]
    if "start" in args:
        body["start"] = _time_field(args["start"], tz)
    if "end" in args:
        body["end"] = _time_field(args["end"], tz)
    if "attendees" in args:
        body["attendees"] = [{"email": a} for a in args["attendees"]]
    return body


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    svc = get_service()

    if name == "list_calendars":
        result = svc.calendarList().list().execute()
        cals = [
            {"id": c["id"], "summary": c.get("summary"), "primary": c.get("primary", False),
             "access_role": c.get("accessRole"), "time_zone": c.get("timeZone")}
            for c in result.get("items", [])
        ]
        return [TextContent(type="text", text=json.dumps(cals, ensure_ascii=False, indent=2))]

    if name == "list_events":
        params: dict[str, Any] = {
            "calendarId": arguments.get("calendar_id", "primary"),
            "timeMin": arguments["time_min"],
            "timeMax": arguments["time_max"],
            "maxResults": arguments.get("max_results", 50),
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if arguments.get("query"):
            params["q"] = arguments["query"]
        result = svc.events().list(**params).execute()
        events = [{
            "id": e["id"],
            "summary": e.get("summary"),
            "start": e.get("start"),
            "end": e.get("end"),
            "location": e.get("location"),
            "attendees": [a.get("email") for a in e.get("attendees", [])],
            "status": e.get("status"),
            "html_link": e.get("htmlLink"),
        } for e in result.get("items", [])]
        return [TextContent(type="text", text=json.dumps(events, ensure_ascii=False, indent=2))]

    if name == "get_event":
        event = svc.events().get(
            calendarId=arguments.get("calendar_id", "primary"),
            eventId=arguments["event_id"],
        ).execute()
        return [TextContent(type="text", text=json.dumps(event, ensure_ascii=False, indent=2))]

    if name == "create_event":
        body = _build_event_body(arguments, tz_default="Europe/Warsaw")
        created = svc.events().insert(
            calendarId=arguments.get("calendar_id", "primary"),
            body=body,
            sendUpdates=arguments.get("send_updates", "none"),
        ).execute()
        return [TextContent(type="text", text=json.dumps({
            "id": created["id"],
            "html_link": created.get("htmlLink"),
            "summary": created.get("summary"),
        }, ensure_ascii=False))]

    if name == "update_event":
        body = _build_event_body(arguments, tz_default="Europe/Warsaw")
        if not body:
            raise ValueError("update_event needs at least one field besides event_id")
        updated = svc.events().patch(
            calendarId=arguments.get("calendar_id", "primary"),
            eventId=arguments["event_id"],
            body=body,
            sendUpdates=arguments.get("send_updates", "none"),
        ).execute()
        return [TextContent(type="text", text=json.dumps({
            "id": updated["id"],
            "html_link": updated.get("htmlLink"),
            "summary": updated.get("summary"),
        }, ensure_ascii=False))]

    if name == "delete_event":
        svc.events().delete(
            calendarId=arguments.get("calendar_id", "primary"),
            eventId=arguments["event_id"],
            sendUpdates=arguments.get("send_updates", "none"),
        ).execute()
        return [TextContent(type="text", text=json.dumps({"deleted": True, "id": arguments["event_id"]}))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
