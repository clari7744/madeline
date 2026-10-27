import discord
from discord.ext import commands
from tabulate import tabulate


class TablePaginator(commands.Paginator):
    """A Paginator that formats tabular data into `fancy_grid` tables per page while ensuring headers are repeated on every page."""

    def __init__(
        self,
        headers: list[str],
        rows: list[list],
        max_rows_per_page: int = 10,
        prefix: str = "```",
        suffix: str = "```",
    ):
        super().__init__(prefix=prefix, suffix=suffix, max_size=1900)
        self.headers = headers
        self.rows = rows
        self.max_rows_per_page = max_rows_per_page
        self._paginate_table()

    def _paginate_table(self):
        """Chunk rows and build individual formatted grid pages."""
        if not self.rows:
            # Handle empty table edge case
            formatted_empty = tabulate([], headers=self.headers, tablefmt="fancy_grid")
            self.add_line(formatted_empty)
            return

        # Split rows into chunks
        for i in range(0, len(self.rows), self.max_rows_per_page):
            chunk = self.rows[i : i + self.max_rows_per_page]
            formatted_chunk = tabulate(chunk, headers=self.headers, tablefmt="fancy_grid")

            # Close the current page if adding this chunk exceeds Discord's max length
            self.add_line(formatted_chunk)
            if i + self.max_rows_per_page < len(self.rows):
                self.close_page()


class TablePaginatorView(discord.ui.View):
    """Discord UI View using buttons to navigate through `TablePaginator` pages."""

    def __init__(
        self,
        author: discord.User | discord.Member,
        paginator: TablePaginator,
        timeout: float = 180.0,
    ):
        super().__init__(timeout=timeout)
        self.author = author
        self.paginator = paginator
        self.current_page = 0
        self.total_pages = len(paginator.pages)
        self.update_buttons()

    def update_buttons(self):
        """Update button states and the middle page indicator button."""
        self.first_page_btn.disabled = self.current_page == 0
        self.prev_page_btn.disabled = self.current_page == 0
        self.next_page_btn.disabled = self.current_page == self.total_pages - 1
        self.last_page_btn.disabled = self.current_page == self.total_pages - 1
        self.page_indicator_btn.label = f"Page {self.current_page + 1}/{self.total_pages}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command caller can click the pagination buttons."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You cannot use these controls.", ephemeral=True)
            return False
        return True

    async def _change_page(self, interaction: discord.Interaction, new_page: int):
        self.current_page = new_page
        self.update_buttons()
        await interaction.response.edit_message(
            content=self.paginator.pages[self.current_page],
            view=self,
        )

    @discord.ui.button(label="≪", style=discord.ButtonStyle.secondary)
    async def first_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, 0)

    @discord.ui.button(label="＜", style=discord.ButtonStyle.primary)
    async def prev_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, self.current_page - 1)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_indicator_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="＞", style=discord.ButtonStyle.primary)
    async def next_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, self.current_page + 1)

    @discord.ui.button(label="≫", style=discord.ButtonStyle.secondary)
    async def last_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, self.total_pages - 1)
