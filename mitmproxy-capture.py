"""
mitmproxy inline script for capturing ZeroMOUSE app traffic.
Filters and logs AWS Cognito tokens, IoT endpoints, and MQTT-related calls.

Usage: mitmweb -s mitmproxy-capture.py
"""

import json
import re
from datetime import datetime
from mitmproxy import http, ctx

CAPTURE_FILE = "zeromouse-captures.json"
captures = []

# Patterns we care about
INTERESTING_HOSTS = [
    "cognito",
    "amazonaws.com",
    "iot.",
    "execute-api",
    "zeromouse",
]

INTERESTING_HEADERS = [
    "x-amz-",
    "authorization",
    "x-api-key",
]


def save_captures():
    with open(CAPTURE_FILE, "w") as f:
        json.dump(captures, f, indent=2, default=str)


def is_interesting(flow: http.HTTPFlow) -> bool:
    host = flow.request.pretty_host.lower()
    return any(pattern in host for pattern in INTERESTING_HOSTS)


def response(flow: http.HTTPFlow):
    if not is_interesting(flow):
        return

    host = flow.request.pretty_host
    url = flow.request.pretty_url
    method = flow.request.method

    entry = {
        "timestamp": datetime.now().isoformat(),
        "method": method,
        "url": url,
        "host": host,
        "status": flow.response.status_code if flow.response else None,
        "request_headers": {},
        "response_headers": {},
        "request_body": None,
        "response_body": None,
    }

    # Capture ALL request headers
    for key, value in flow.request.headers.items():
        entry["request_headers"][key] = value

    # Capture ALL response headers
    if flow.response:
        for key, value in flow.response.headers.items():
            entry["response_headers"][key] = value

    # Capture request body
    if flow.request.content:
        try:
            body = flow.request.content.decode("utf-8", errors="replace")
            # Try to parse as JSON for readability
            try:
                entry["request_body"] = json.loads(body)
            except json.JSONDecodeError:
                entry["request_body"] = body[:2000]
        except Exception:
            entry["request_body"] = f"<binary {len(flow.request.content)} bytes>"

    # Capture response body
    if flow.response and flow.response.content:
        try:
            body = flow.response.content.decode("utf-8", errors="replace")
            try:
                entry["response_body"] = json.loads(body)
            except json.JSONDecodeError:
                entry["response_body"] = body[:2000]
        except Exception:
            entry["response_body"] = f"<binary {len(flow.response.content)} bytes>"

    captures.append(entry)
    save_captures()

    # Print highlights to the mitmproxy event log
    ctx.log.info(f"[ZM] {method} {url} -> {entry['status']}")

    # Flag the most valuable captures
    resp_str = json.dumps(entry.get("response_body", ""))
    req_str = json.dumps(entry.get("request_body", ""))

    if "cognito" in host.lower():
        ctx.log.warn(f"[ZM] *** COGNITO AUTH *** {url}")

    if any(tok in resp_str for tok in ["IdToken", "AccessToken", "IdentityId", "Credentials"]):
        ctx.log.warn(f"[ZM] *** TOKENS FOUND IN RESPONSE ***")

    if any(tok in req_str for tok in ["IdToken", "AccessToken", "IdentityId"]):
        ctx.log.warn(f"[ZM] *** TOKENS IN REQUEST ***")

    if "iot" in host.lower() or "mqtt" in url.lower():
        ctx.log.warn(f"[ZM] *** IOT/MQTT ENDPOINT *** {url}")
