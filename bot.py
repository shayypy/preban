import guilded
from guilded.ext import commands

from prisma import Prisma

import os
from dotenv import load_dotenv
load_dotenv('.env')

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            'pb/',
            description='Preemptively ban users from your server.',
            owner_id='EdVMVKR4',
            help_command=commands.MinimalHelpCommand(),
            experimental_event_style=True,
        )
        self.prisma: Prisma = None

    async def on_ready(self):
        print(f'Ready - {self.user} ({self.user_id})')
        if not self.user.status:
            await self.set_status(90002019, content=f'pb/help')

    async def on_message(self, event: guilded.MessageEvent):
        if event.server and len(event.server.roles) < 1:
            await event.server.fill_roles()

        await self.process_commands(event.message)

    async def setup_hook(self):
        self.prisma = Prisma()
        await self.prisma.connect()

        self.load_extension('main')


bot = Bot()

@bot.command()
@commands.is_owner()
async def reload(ctx: commands.Context):
    bot.reload_extension('main')
    await ctx.message.add_reaction(90002171)

bot.run(os.environ.get('TOKEN'))
