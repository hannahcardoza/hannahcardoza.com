#!/usr/bin/env python3
"""One-time Spotify sign-in for the Web Log dashboard.

Run this yourself in a terminal:

    python3 scripts/spotify_auth.py

It asks for your Spotify app's Client ID and Client Secret (typed input is
hidden for the secret), opens Spotify in your browser so you can approve
access, then saves three GitHub Actions secrets with the `gh` CLI:
SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN.
It also writes them to a local .env file (ignored by git) so the dashboard
can be tested locally. Nothing is printed.

The Spotify app must list this exact Redirect URI:
    http://127.0.0.1:8888/callback
"""

import base64
import getpass
import http.server
import json
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-recently-played user-top-read playlist-read-private"


def wait_for_code(expected_state):
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            if q.get("state", [""])[0] != expected_state:
                result["error"] = "state mismatch"
            elif "error" in q:
                result["error"] = q["error"][0]
            else:
                result["code"] = q.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Done. You can close this tab." if "code" in result else f"Error: {result.get('error')}"
            self.wfile.write(f"<p style='font-family:sans-serif'>{msg}</p>".encode())

        def log_message(self, *args):
            pass

    with http.server.HTTPServer(("127.0.0.1", 8888), Handler) as server:
        while not result:
            server.handle_request()
    if "error" in result:
        sys.exit(f"Spotify sign-in failed: {result['error']}")
    return result["code"]


def exchange(code, client_id, client_secret):
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request("https://accounts.spotify.com/api/token", data=body,
                                 headers={"Authorization": f"Basic {auth}",
                                          "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["refresh_token"]


def set_secret(name, value):
    subprocess.run(["gh", "secret", "set", name], input=value.encode(), check=True,
                   stdout=subprocess.DEVNULL)


def write_env(values):
    """Merge values into .env at the repo root (gitignored), for local testing."""
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / ".env"
    lines = path.read_text().splitlines() if path.exists() else []
    lines = [l for l in lines if l.split("=", 1)[0] not in values]
    lines += [f"{k}={v}" for k, v in values.items()]
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)


def main():
    client_id = input("Spotify Client ID: ").strip()
    client_secret = getpass.getpass("Spotify Client Secret (hidden): ").strip()
    if not client_id or not client_secret:
        sys.exit("Both values are required.")

    state = secrets.token_urlsafe(16)
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    })
    print("Opening Spotify in your browser. Click Agree to continue.")
    webbrowser.open(url)
    code = wait_for_code(state)
    refresh_token = exchange(code, client_id, client_secret)

    print("Saving GitHub secrets...")
    set_secret("SPOTIFY_CLIENT_ID", client_id)
    set_secret("SPOTIFY_CLIENT_SECRET", client_secret)
    set_secret("SPOTIFY_REFRESH_TOKEN", refresh_token)
    write_env({"SPOTIFY_CLIENT_ID": client_id, "SPOTIFY_CLIENT_SECRET": client_secret,
               "SPOTIFY_REFRESH_TOKEN": refresh_token})
    print("Done. Spotify is connected. SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and "
          "SPOTIFY_REFRESH_TOKEN are saved as GitHub secrets.")


if __name__ == "__main__":
    main()
