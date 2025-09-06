# Project Sphere Palworld
 > [!WARNING]  
 > This bot is still in development, but it's in a usable state. No support will be provided unless it's for bug reports or feature requests.

 Sphere is a Discord bot for Palworld servers. It lets you control servers, log players, manage bans and whitelists, cross-server chat, backups, and more. The SFTP branch adds support for reading server logs and chat directly over SFTP.

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
 - **Null Check**: This will check for players joining without a valid user id and kick them. (Experimental)
 - **Cross Server Chat**: Send and receive chats from the server to discord and vice versa.
 - **Scheduled Backups**: Create backups of your server and send them to a discord channel at timed intervals.
 - **SFTP Support**: Securely connect to your servers via SFTP for automated save checks, remote file transfers, and backup uploads.

## Environment Variables
- `BOT_TOKEN`: Your discord bot token generated on the [Discord Developer Portal](https://discord.com/developers/applications).
- `BOT_PREFIX`: The prefix used for non slash commands. Example `!`
- `API_URL`: API URL if you setup the [Banlist API](https://github.com/projectsphere/banlist-api).
- `API_KEY`: The API Key you set for your banlist. This key is used to access the endpoints securely.

## Installation
 1. Create a `.env` file and fill out your `BOT_TOKEN` and `BOT_PREFIX`
 2. Run the bot with `python main.py`
 3. Use `/help` to see all available commands on the bot.

## Example YML Configuration
SFTP configuration is done through a yaml file named `sftp.yml`. Below is an example configuration for multiple servers. 
 ```YML
 servers:
  - name: "Palworld Server"
    host: "192.168.1.10"
    port: 2022
    username: "user1"
    password: "password1"
    path: "Pal/Binaries/Win64/PalDefender/Logs"
    webhook: "https://discord.com/api/webhooks/111111111111111111/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    channel: 111111111111111111
    save_path: "Pal/Saved/SaveGames/0/0000000000000001"
    backup_channel: 111111111111111111
    backup_interval: 300
 ```


## This project runs my libaries.
 - **Palworld API** - A python library that acts as a wrapper for the Palworld server REST API.
 - **GameRCON** - An asynchronous RCON library designed to handle multiple RCON tasks across numerous servers.