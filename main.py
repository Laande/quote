import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from create_gif import create_dynamic_gif
import requests


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


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


@bot.event
async def on_ready():
    print(f"Connected as {bot.user}")
    await bot.tree.sync()
    update_status.start()


@bot.tree.context_menu(name="Quote")
async def quote_context(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer()
    if not message.content:
        await interaction.followup.send(
            "This message has no text content to quote", ephemeral=True
        )
        return
    try:
        gif_buf = create_dynamic_gif(message.author.display_name, message.content)
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
        gif_buf = create_dynamic_gif(msg.author.display_name, msg.content)
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
        gif_buf = create_dynamic_gif(msg.author.display_name, msg.content)
        await interaction.followup.send(file=discord.File(gif_buf, filename="quote.gif"))
    except Exception as e:
        print(f"Error creating GIF: {e}")
        await interaction.followup.send("Failed to create GIF for this message.", ephemeral=True)


if __name__ == "__main__":
    load_dotenv()
    bot.run(os.getenv("TOKEN"))