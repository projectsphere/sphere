import discord
from discord.ext import commands
import utils.settings as settings
from utils.errorhandling import setup_logging, STARTUP_CHECK
import utils.constants as c
import logging

setup_logging()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=settings.bot_prefix, intents=intents)

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

bot.setup_hook = lambda: settings.setup_hook(bot)

@bot.event
async def on_ready():
    print(f'{c.SPHERE_MESSAGE}')
    print(f"Your bot is in {len(bot.guilds)} servers and serving {len(bot.users)} users.")
    print(f"Invite link: {discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=8))}")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Palworld"))

@bot.command()
@commands.is_owner()
async def load(ctx, extension):
    try:
        await bot.load_extension(f"cogs.{extension}")
        await ctx.send(f"Loaded {extension} successfully.")
    except Exception as e:
        await ctx.send(f"Failed to load {extension}. {type(e).__name__}: {e}")

@bot.command()
@commands.is_owner()
async def unload(ctx, extension):
    try:
        await bot.unload_extension(f"cogs.{extension}")
        await ctx.send(f"Unloaded {extension} successfully.")
    except Exception as e:
        await ctx.send(f"Failed to unload {extension}. {type(e).__name__}: {e}")

@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    try:
        await bot.unload_extension(f"cogs.{extension}")
        await bot.load_extension(f"cogs.{extension}")
        await ctx.send(f"Reloaded {extension} successfully.")
    except Exception as e:
        await ctx.send(f"Failed to reload {extension}. {type(e).__name__}: {e}")

if __name__ == '__main__':
    logging.info(bytes.fromhex(STARTUP_CHECK).decode())
    bot.run(settings.bot_token)