from flask import Flask, request, redirect
import requests
import json
import os

app = Flask(__name__)

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")  # Must match your Render URL exactly

def save_token(user_id, token_data):
    try:
        with open("tokens.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data[str(user_id)] = token_data
    with open("tokens.json", "w") as f:
        json.dump(data, f, indent=4)

@app.route("/oauth/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided", 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds.join"
    }

    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return f"Token exchange failed: {r.text}", 400

    tokens = r.json()
    user_info = requests.get("https://discord.com/api/users/@me", headers={
        "Authorization": f"Bearer {tokens['access_token']}"
    }).json()

    save_token(user_info["id"], tokens)
    return f"✅ Verification complete: {user_info['username']}"

@app.route("/")
def index():
    return "OAuth Server Online"

