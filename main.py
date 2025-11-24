import os
import requests
import json
import discord
from discord.ext import tasks
from discord import app_commands
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from create_gif import create_dynamic_gif


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
STATS_FILE = "bot_stats.json"
executor = ThreadPoolExecutor(max_workers=2)


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
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=quote))


@tasks.loop(hours=10)
async def update_server_count():
    app_info = await client.application_info()
    stats["servers_count"] = app_info.approximate_guild_count
    stats["users_count"] = app_info.approximate_user_install_count
    save_stats(stats)


@client.event
async def on_ready():
    print(f"Connected as {client.user}")
    await tree.sync()
    update_server_count.start()
    update_status.start()


def make_gif(author, text):
    stats["gifs_generated"] += 1
    save_stats(stats)
    
    future = executor.submit(create_dynamic_gif, author, text)
    return future.result()


@tree.context_menu(name="Quote")
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


@tree.command(name="quote", description="Create a GIF quote from a message link or ID")
@app_commands.describe(message_link="Message link or ID to quote")
async def quote(interaction: discord.Interaction, message_id: str):
    await interaction.response.defer()
    
    try:
        msg_id = int(message_id.split("/")[-1])
        msg = await interaction.channel.fetch_message(msg_id)
    except Exception:
        await interaction.followup.send("Invalid message ID or link", ephemeral=True)
        return

    if not msg.content:
        await interaction.followup.send("This message has no text content to quote", ephemeral=True)
        return

    try:
        gif_buf = make_gif(msg.author.display_name, msg.content)
        await interaction.followup.send(file=discord.File(gif_buf, filename="quote.gif"))
    except Exception as e:
        print(f"Error creating GIF: {e}")
        await interaction.followup.send("Failed to create GIF", ephemeral=True)


@tree.command(name="customquote", description="Create a custom GIF quote with your own text")
@app_commands.describe(
    text="The quote text to display",
    author="Author name (optional, defaults to your username)"
)
async def customquote(interaction: discord.Interaction, text: str, author: str = None):
    await interaction.response.defer()
    
    if len(text) > 500:
        await interaction.followup.send("Text is too long, maximum 500 characters", ephemeral=True)
        return
    
    author_name = author if author else interaction.user.display_name
    
    try:
        gif_buf = make_gif(author_name, text)
        await interaction.followup.send(file=discord.File(gif_buf, filename="quote.gif"))
    except Exception as e:
        print(f"Error creating GIF: {e}")
        await interaction.followup.send("Failed to create GIF", ephemeral=True)


@tree.command(name="help", description="Show how to use the Quote bot")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Quote Bot",
        description="Create animated GIF quotes from Discord messages",
        color=discord.Color.dark_embed()
    )
    
    embed.add_field(
        name="Context Menu",
        value="Right-click on a message → **Apps** → **Quote**",
        inline=False
    )
    
    embed.add_field(
        name="Slash command with message ID or link",
        value="`/quote <id>`\nRight-click message → **Copy Message Link** or **Copy Message ID** → Paste in command",
        inline=False
    )
    
    embed.add_field(
        name="Custom quote",
        value="`/customquote <your text> [author name]`\nCreate a quote with your own text!",
        inline=False
    )
    
    embed.set_footer(text="Support: discord.gg/EbJduC5gE2")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    load_dotenv()
    client.run(os.getenv("TOKEN"))