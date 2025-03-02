import os
from dotenv import load_dotenv
from utils.database import initialize_db

load_dotenv()
bot_token = os.getenv('BOT_TOKEN', "No token found")
bot_prefix = os.getenv('BOT_PREFIX', "!")

async def setup_hook(bot):
    await initialize_db()
    for root, _, files in os.walk("./cogs"):
        for filename in files:
            if filename.endswith(".py"):
                extension = os.path.join(root, filename).replace(os.sep, ".")[2:-3]
                await bot.load_extension(extension)
    await bot.tree.sync()