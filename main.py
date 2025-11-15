import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from create_gif import create_dynamic_gif
import requests
import json


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
STATS_FILE = "bot_stats.json"


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {"gifs_generated": 0, "servers_count": 0}


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

stats = load_stats()


async def fetch_random_quote():
    try:
        req = requests.get("http://api.quotable.io/random", timeout=5)
        if req.status_code == 200:
            data = req.json()
            return f"{data['content']} - {data['author']}"
        else:
            return "An inspirational quote. - Lande"
    except Exception as e:
        print(f"Failed to fetch quote: {e}")
        return "An inspirational quote. - Lande"


@tasks.loop(minutes=30)
async def update_status():
    quote = await fetch_random_quote()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=quote))


@tasks.loop(hours=10)
async def update_server_count():
    app_info = await bot.application_info()
    stats["servers_count"] = app_info.approximate_guild_count
    stats["users_count"] = app_info.approximate_user_install_count
    save_stats(stats)


@bot.event
async def on_ready():
    print(f"Connected as {bot.user}")
    await bot.tree.sync()
    update_server_count.start()
    update_status.start()


def make_gif(author, text):
    stats["gifs_generated"] += 1
    save_stats(stats)
    return create_dynamic_gif(author, text)


@bot.tree.context_menu(name="Quote")
async def quote_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer()
    if not message.content:
        await interaction.followup.send(
            "This message has no text content to quote", ephemeral=True
        )
        return
    try:
        gif_buf = make_gif(message.author.display_name, message.content)
        await interaction.followup.send(
            file=discord.File(gif_buf, filename="quote.gif")
        )
    except Exception as e:
        print(f"Error creating GIF: {e}")
        await interaction.followup.send("Failed to create GIF for this message", ephemeral=True)

@bot.command(name="quote")
async def quote_cmd(ctx, *, arg=None):
    msg = None
    if ctx.message.reference:
        msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    elif arg:
        try:
            msg_id = int(arg.split("/")[-1])
            msg = await ctx.channel.fetch_message(msg_id)
        except Exception:
            return await ctx.send("Invalid message ID or link.")
    else:
        return await ctx.send("Please reply to a message or provide a message ID/link.")

    if not msg.content:
        return await ctx.send("The target message has no text content.")

    try:
        gif_buf = make_gif(msg.author.display_name, msg.content)
        await ctx.send(file=discord.File(gif_buf, filename="quote.gif"))
    except Exception as e:
        print(f"Error creating GIF: {e}")
        await ctx.send("Failed to create GIF for this message.")


@bot.tree.command(name="quote", description="Create a GIF quote from a message")
@app_commands.describe(message_id="Provide message ID or link")
async def quote(interaction: discord.Interaction, message_id: str = None):
    await interaction.response.defer()
    msg = None

    if not message_id:
        await interaction.followup.send("Please provide a message ID or link.", ephemeral=True)
        return

    try:
        msg_id = int(message_id.split("/")[-1])
        msg = await interaction.channel.fetch_message(msg_id)
    except Exception:
        await interaction.followup.send("Invalid message ID or link.", ephemeral=True)
        return

    if not msg.content:
        await interaction.followup.send("The target message has no text content.", ephemeral=True)
        return

    try:
        gif_buf = make_gif(msg.author.display_name, msg.content)
        await interaction.followup.send(file=discord.File(gif_buf, filename="quote.gif"))
    except Exception as e:
        print(f"Error creating GIF: {e}")
        await interaction.followup.send("Failed to create GIF for this message.", ephemeral=True)


@bot.tree.command(name="help", description="Show how to use the Quote bot")
async def help_cmd(interaction: discord.Interaction):
    message = (
        "- Can be used by right-clicking a message, then selecting **Apps → Quote**\n"
        "- It also works with `!quote [msg]`\n"
        "the `msg` argument is optional; you can simply reply to the message you want to quote with the command\n"
        "- It also works as a slash command: `/quote <msg>`\n"
        "where `msg` can be the message ID or its URL\n\n"
        "[Support server](https://discord.gg/EbJduC5gE2)"
    )
    await interaction.response.send_message(message, ephemeral=True)


if __name__ == "__main__":
    load_dotenv()
    bot.run(os.getenv("TOKEN"))