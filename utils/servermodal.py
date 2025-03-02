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
