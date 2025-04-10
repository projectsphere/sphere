# Project Sphere Palworld
 > [!WARNING]  
 > This bot is still in development, but it's in a usable state. No support will be provided unless it's for bug reports or feature requests.

 This bot is designed to be a server management replacement for my current [Palbot](https://github.com/dkoz/palworld-palbot) project. Unlike Palbot, which only supports Steam servers, this new project is created to support both Xbox and Steam servers.

## Features:
 - **Server Management**: Ability to control your servers directly from the bot.
 - **Player Logging**: Log extensive information about players who are active on your servers.
 - **Connection Events**: Logs and reports players connecting to the server.
 - **Ban List Logger**: When players are banned through the bot, it will be logged in the SQL database with the reason.
 - **Whitelist Management**: Allows you to enable a whitelist for your server so only select users can play.
 - **Administration Control**: Allows you to kick, ban, and manage players on your server directly from the bot.
 - **Server Query**: Allows you query servers added to the bot.
 - **Global Banlist**: This will allow you to global ban across all your servers using the [Sphere Banlist API](https://github.com/projectsphere/banlist-api).
 - **PalDefender**: Gives basic functionality of PalDefender rcon commands.
 - **VAC Check**: This will run checks on steam users to make sure they're not VAC Banned or spoofing. (Experimental)
 - **Null Check**: This will check for players joining without a valid user id and kick them. (Experimental)
 - **Cross Server Chat**: Send and receive chats from the server to discord and vice versa.

## Environment Variables
- `BOT_TOKEN`: Your discord bot token generated on the [Discord Developer Portal](https://discord.com/developers/applications).
- `BOT_PREFIX`: The prefix used for non slash commands. Example `!`
- `API_URL`: API URL if you setup the [Banlist API](https://github.com/projectsphere/banlist-api).
- `API_KEY`: The API Key you set for your banlist. This key is used to access the endpoints securely.
- `STEAM_API_KEY`: Your Steam API key for running checks on spoofers and cheaters.

## Installation
 1. Create a `.env` file and fill out your `BOT_TOKEN` and `BOT_PREFIX`
 2. Run the bot with `python main.py`
 3. Use `/help` to see all available commands on the bot.

## This project runs my libaries.
 - **Palworld API Wrapper** - A python library that acts as a wrapper for the Palworld server REST API.
 - **GameRCON** - An asynchronous RCON library designed to handle multiple RCON tasks across numerous servers.