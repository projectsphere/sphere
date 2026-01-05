import discord

# I really need to make a pagination pip package

class Pagination:
    def __init__(self, items, page_size=10):
        self.items = items
        self.page_size = page_size
        self.total_pages = len(items) // page_size + (1 if len(items) % page_size > 0 else 0)

    def get_page(self, page_number):
        start = (page_number - 1) * self.page_size
        end = start + self.page_size
        return self.items[start:end]

class PaginationView(discord.ui.View):
    def __init__(self, paginator, current_page, embed_creator):
        super().__init__()
        self.paginator = paginator
        self.current_page = current_page
        self.embed_creator = embed_creator
        self.add_pagination_buttons()

    def add_pagination_buttons(self):
        if self.current_page > 1:
            self.add_item(PaginationButton("Previous", -1, self))

        if self.current_page < self.paginator.total_pages:
            self.add_item(PaginationButton("Next", 1, self))

    async def update_page(self, interaction, page_delta):
        self.current_page += page_delta
        new_embed = self.embed_creator(self.paginator.get_page(self.current_page), self.current_page, self.paginator.total_pages)
        await interaction.response.edit_message(embed=new_embed, view=PaginationView(self.paginator, self.current_page, self.embed_creator))

class PaginationButton(discord.ui.Button):
    def __init__(self, label, page_delta, pagination_view):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.page_delta = page_delta
        self.pagination_view = pagination_view

    async def callback(self, interaction: discord.Interaction):
        await self.pagination_view.update_page(interaction, self.page_delta)
