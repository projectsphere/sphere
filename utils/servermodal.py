import discord

class AddServerModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.TextInput(label="Server Name", placeholder="Enter your server name here"))
        self.add_item(discord.ui.TextInput(label="Host", placeholder="Enter your server's IP address here"))
        self.add_item(discord.ui.TextInput(label="Admin Password", placeholder="Enter your server's admin password here"))
        self.add_item(discord.ui.TextInput(label="REST API Port", placeholder="Enter your server's RESTAPI port here", style=discord.TextStyle.short))
        self.add_item(discord.ui.TextInput(label="RCON Port", placeholder="Enter your server's RCON port here", style=discord.TextStyle.short))

    async def on_submit(self, interaction: discord.Interaction):
        pass

class ChatSetupModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.TextInput(label="Chatlog Channel ID", placeholder="Channel ID for logs and relay"))
        self.add_item(discord.ui.TextInput(label="Chatlog Path", placeholder="Path to your server logs"))
        self.add_item(discord.ui.TextInput(label="Webhook URL", placeholder="Webhook to post chat messages"))

    async def on_submit(self, interaction: discord.Interaction):
        pass

class BackupModal(discord.ui.Modal):
    def __init__(self, *args, on_submit_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_submit_callback = on_submit_callback
        self.add_item(discord.ui.TextInput(label="Channel ID", placeholder="Destination channel ID"))
        self.add_item(discord.ui.TextInput(label="Save Path", placeholder="Full path to save folder"))
        self.add_item(discord.ui.TextInput(label="Interval (minutes)", placeholder="Backup interval in minutes"))

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_callback(interaction, self)