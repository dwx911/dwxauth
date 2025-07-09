import os
import discord
from discord.ext import commands
import json
import requests

TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
REDIRECT_URI = os.environ.get("REDIRECT_URI")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_tokens():
    try:
        with open("tokens.json", "r") as f:
            return json.load(f)
    except:
        return {}

@bot.command()
async def verify(ctx):
    auth_url = (
        f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code&scope=identify%20guilds.join"
    )
    try:
        await ctx.author.send(f"Click this link to verify and authorize: {auth_url}")
        await ctx.send("I've sent you a DM with the verification link!")
    except discord.Forbidden:
        await ctx.send("I can't DM you. Please enable DMs and try again.")

@bot.command()
@commands.has_permissions(administrator=True)
async def joinuser(ctx, user_id: int, guild_id: int):
    tokens = load_tokens()
    token_data = tokens.get(str(user_id))
    if not token_data:
        await ctx.send("That user hasn't verified or I don't have their token.")
        return

    headers = {
        "Authorization": f"Bot {TOKEN}",
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
        await ctx.send(f"✅ User <@{user_id}> added to the server.")
    else:
        await ctx.send(f"❌ Failed to add user: {r.status_code} - {r.text}")

@bot.command()
@commands.has_permissions(administrator=True)
async def listverified(ctx):
    tokens = load_tokens()
    if not tokens:
        await ctx.send("No users have verified yet.")
        return

    verified_users = "\n".join([f"<@{uid}>" for uid in tokens.keys()])
    await ctx.send(f"Verified users:\n{verified_users}")

bot.run(TOKEN)
