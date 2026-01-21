import os
import requests
import json
import discord
from discord.ext import tasks
from discord import app_commands
from dotenv import load_dotenv
from create_gif import create_dynamic_gif
import asyncio


intents = discord.Intents.default()
client = discord.Client(
    intents=intents,
    max_messages=None,
    member_cache_flags=discord.MemberCacheFlags.none()
)
tree = app_commands.CommandTree(client)
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


def _fetch_quote_sync():
    req = requests.get("http://api.quotable.io/random", timeout=5)
    if req.status_code == 200:
        data = req.json()
        return f"{data['content']} - {data['author']}"
    return "An inspirational quote. - Lande"


async def fetch_random_quote():
    try:
        return await asyncio.to_thread(_fetch_quote_sync)
    except Exception as e:
        print(f"Failed to fetch quote: {e}")
        return "An inspirational quote. - Lande"


@tasks.loop(minutes=30)
async def update_status():
    quote = await fetch_random_quote()
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=quote))


@tasks.loop(hours=10)
async def update_server_count():
    try:
        app_info = await client.application_info()
        stats["servers_count"] = app_info.approximate_guild_count
        stats["users_count"] = app_info.approximate_user_install_count
        save_stats(stats)
    except AttributeError:
        stats["servers_count"] = len(client.guilds)
        stats["users_count"] = len(client.users)
        save_stats(stats)


@client.event
async def on_ready():
    print(f"Connected as {client.user}")
    await tree.sync()
    update_server_count.start()
    update_status.start()


async def make_gif(author, text):
    stats["gifs_generated"] += 1
    save_stats(stats)
    
    result = await asyncio.to_thread(create_dynamic_gif, author, text)
    return result

async def send_quote_gif(interaction, author_name, text):
    if not text:
        await interaction.followup.send("No text to generate a quote.", ephemeral=True)
        return
    
    gif_buf = None
    try:
        gif_buf = await make_gif(author_name, text)
        file = discord.File(fp=gif_buf, filename="quote.gif")
        await interaction.followup.send(file=file)
    except Exception as e:
        print(f"Error creating GIF: {e}")
        await interaction.followup.send("Failed to create GIF", ephemeral=True)
    finally:
        if gif_buf is not None:
            gif_buf.close()
            del gif_buf

async def handle_quote(interaction: discord.Interaction, message: discord.Message):
    if not message.content:
        has_content = message.attachments or message.embeds or message.stickers
        
        if has_content:
            await interaction.followup.send("This message has no text content to quote", ephemeral=True)
        else:
            error_msg = "This message has no text content to quote"
            if interaction.is_guild_integration():
                error_msg += "\n-# Try installing the bot as User Install to resolve permission issues (Click on the bot -> Add app -> Add to my apps)"
            
            await interaction.followup.send(error_msg, ephemeral=True)
        return
    
    if len(message.content) > 500:
        await interaction.followup.send(f"Message too long ({len(message.content)} characters). Maximum is 500 characters.", ephemeral=True)
        return
    
    await send_quote_gif(interaction, message.author.display_name, message.content)

@tree.context_menu(name="Quote")
async def quote_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer()
    await handle_quote(interaction, message)


@tree.command(name="quote", description="Create a GIF quote from a message link or ID")
@app_commands.describe(message_link="Message link or ID to quote")
async def quote_cmd(interaction: discord.Interaction, message_link: str):
    await interaction.response.defer()

    if interaction.guild is None:
        await interaction.followup.send("This command can only be used in a server", ephemeral=True)
        return
    
    try:
        parts = message_link.split("/")
        if len(parts) >= 3 and "discord.com/channels/" in message_link:
            guild_id = int(parts[-3])
            channel_id = int(parts[-2])
            msg_id = int(parts[-1])

            if guild_id != interaction.guild_id:
                await interaction.followup.send("Cannot quote messages from other servers", ephemeral=True)
                return

            channel = await client.fetch_channel(channel_id)
            msg = await channel.fetch_message(msg_id)
        else:
            msg_id = int(message_link)
            msg = await interaction.channel.fetch_message(msg_id)

    except ValueError:
        await interaction.followup.send("Invalid message link or ID format", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.followup.send("Message not found", ephemeral=True)
        return
    except discord.Forbidden:
        await interaction.followup.send("Bot doesn't have permission to access that message", ephemeral=True)
        return
    except Exception:
        await interaction.followup.send("Failed to fetch message", ephemeral=True)
        return

    await handle_quote(interaction, msg)


@tree.command(name="customquote", description="Create a custom GIF quote with your own text")
@app_commands.describe(text="The quote text to display")
async def customquote(interaction: discord.Interaction, text: str):
    await interaction.response.defer()

    if len(text) > 500:
        await interaction.followup.send(f"Text is too long ({len(text)} characters), maximum 500 characters", ephemeral=True)
        return

    await send_quote_gif(interaction, interaction.user.display_name, text)


@tree.command(name="help", description="Show how to use the Quote bot")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
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
        value="`/customquote <your text>`\nCreate a quote with your own text",
        inline=False
    )
    
    embed.set_footer(text="Support: discord.gg/EbJduC5gE2")
    
    await interaction.followup.send(embed=embed)


if __name__ == "__main__":
    load_dotenv()
    client.run(os.getenv("TOKEN"))