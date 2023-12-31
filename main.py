from __future__ import annotations
import datetime
import sys
import traceback
from typing import TYPE_CHECKING
import guilded
from guilded.ext import commands

if TYPE_CHECKING:
    from bot import Bot


class Main(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, event: guilded.MemberJoinEvent):
        member = event.member

        entry = await self.bot.prisma.preban.find_first(
            where={
                'AND': [
                    {'server_id': event.server_id},
                    {'user_id': member.id},
                ],
            },
        )
        if not entry:
            return
        if entry.fulfilled_at or not entry.active:
            # This entry was fulfilled in the past.
            # A moderator probably unbanned the user manually,
            # so we ignore the entry now.
            return

        try:
            created_by = await event.server.getch_member(entry.created_by_id)
            reason = f'Preban by {created_by.name} ({created_by.id})'
        except:
            reason = f'Preban by user with ID {entry.created_by_id}'

        if entry.reason:
            reason += f': {entry.reason}'

        try:
            await member.ban(reason=reason)
        except guilded.HTTPException:
            traceback.print_exc()
            return

    @commands.Cog.listener()
    async def on_ban_create(self, event: guilded.BanCreateEvent):
        # Just in case something else fulfills the preban before we get to it
        await self.bot.prisma.preban.update(
            where={
                'server_id_user_id': {
                    'server_id': event.server_id,
                    'user_id': event.ban.user.id,
                },
            },
            data={
                'fulfilled_at': event.ban.created_at,
                'active': False,
            },
        )

    @commands.command()
    @commands.has_server_permissions(ban_members=True)
    @commands.bot_has_server_permissions(ban_members=True)
    @commands.server_only()
    async def ban(self, ctx: commands.Context, user_id: str, *, reason: str = None):
        """Preban a user. You must provide the ~8 character user ID.\n\n
        Once a ban is fulfilled (a prebanned user joins the server), the user \
        **will not** be banned a second time if the ban is manually lifted by \
        a server admin. Use `pb/ban` again to reactivate a preban."""
        try:
            await self.bot.getch_user(user_id)
        except:
            await ctx.reply('Could not verify that user ID.', silent=True)
            return

        try:
            member = await ctx.server.getch_member(user_id)
        except:
            member = None
        else:
            if member.is_owner() or member == ctx.me:
                await ctx.reply(
                    'I cannot ban the server owner or myself.',
                    silent=True,
                )
                return

        await self.bot.prisma.preban.upsert(
            where={
                'server_id_user_id': {
                    'server_id': ctx.server.id,
                    'user_id': user_id,
                },
            },
            data={
                'create': {
                    'server_id': ctx.server.id,
                    'user_id': user_id,
                    'created_at': datetime.datetime.utcnow(),
                    'created_by_id': ctx.author.id,
                    # Guilded does not seem to actually have a limit for this value
                    # but we set a reasonable limit anyway
                    'reason': reason[:1000] if reason else None,
                    'active': member is None,
                    'fulfilled_at': datetime.datetime.utcnow() if member is not None else None,
                },
                'update': {
                    'created_at': datetime.datetime.utcnow(),
                    'created_by_id': ctx.author.id,
                    'reason': reason[:1000] if reason else None,
                    'active': member is None,
                    'fulfilled_at': datetime.datetime.utcnow() if member is not None else None,
                },
            },
        )

        if member:
            try:
                await member.ban(reason=f'Preban by {ctx.author.name} ({ctx.author.id})')
            except:
                await ctx.reply(
                    'I created a preban entry, but I was unable to ban this '
                    'user (they are currently a member). Please verify my '
                    'permissions and make sure you are not attempting to '
                    'preban a member who ranks higher than me.',
                    silent=True,
                )
            else:
                await ctx.reply(
                    'Banned this user and created a preban entry.',
                    silent=True,
                )
        else:
            await ctx.reply(
                'Prebanned this user. Make sure I do not lose the **Kick / Ban members** permission.',
                silent=True,
            )

    @commands.command()
    @commands.has_server_permissions(ban_members=True)
    @commands.bot_has_server_permissions(ban_members=True)
    @commands.server_only()
    async def unban(self, ctx: commands.Context, user_id: str):
        """Remove a preban.\n
        This will also unban the user from the server if they are currently banned."""
        try:
            await self.bot.getch_user(user_id)
        except:
            await ctx.reply('Could not verify that user ID.', silent=True)
            return

        try:
            member_ban = await ctx.server.fetch_ban(guilded.Object(user_id))
        except:
            member_ban = None

        if member_ban:
            try:
                await ctx.server.unban(guilded.Object(user_id))
            except:
                pass

        entry = await self.bot.prisma.preban.find_first(
            where={
                'AND': [
                    {'server_id': ctx.server.id},
                    {'user_id': user_id},
                ],
            },
        )
        if not entry:
            await ctx.reply(
                'This user was not banned or prebanned.'
                if not member_ban else
                'This user was not prebanned, but they have been unbanned.',
                silent=True,
            )
            return

        await self.bot.prisma.preban.delete(
            where={
                'server_id_user_id': {
                     'server_id': ctx.server.id,
                     'user_id': user_id,
                 },
            },
        )
        # Does it make sense to keep the preban entry?
        # await self.bot.prisma.preban.update(
        #     where={
        #         'server_id_user_id': {
        #             'server_id': ctx.server.id,
        #             'user_id': user_id,
        #         },
        #     },
        #     data=(
        #         {'fulfilled_at': member_ban.created_at, 'active': False}
        #         if member_ban else
        #         {'active': False}
        #     ),
        # )

        await ctx.reply(
            'Removed the preban for this user.',
            silent=True,
        )

    @commands.command()
    @commands.has_server_permissions(ban_members=True)
    @commands.bot_has_server_permissions(ban_members=True)
    @commands.server_only()
    async def bans(self, ctx: commands.Context):
        """List all registered prebans."""
        prebans = await self.bot.prisma.preban.find_many(
            where={
                'server_id': ctx.server.id,
            },
        )

        embed = guilded.Embed(
            title=f'{len(prebans):,} Preban{"s" if len(prebans) != 1 else ""}',
            description='',
        )
        for preban in prebans:
            line = ''
            if preban.active:
                line += ':timer_clock:'
            elif preban.fulfilled_at:
                line += ':white_check_mark:'
            else:
                line += ':x:'

            line += f' `{preban.user_id}` by <@{preban.created_by_id}>'
            if preban.fulfilled_at:
                line += f' - fulfilled: {preban.fulfilled_at.strftime("%b %-d, %Y")}'
            line += '\n'

            if len(embed.description + line) >= 2048:
                break
            embed.description += line

        if not embed.description:
            embed.description = f'This server has no prebans. Create one with `{ctx.prefix}ban`.'
        else:
            remaining = len(prebans) - len(embed.description.strip().splitlines())
            if remaining > 0:
                embed.set_footer(text=(
                    f'{remaining:,} more prebans not listed. '
                    'This is a current limitation. Sorry.'
                ))

        await ctx.reply(
            embed=embed,
            silent=True,
        )


class Errors(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: guilded.GuildedException):
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound,)
        error = getattr(error, 'original', error)
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.NotOwner):
            return await ctx.reply('This command is owner-only.', private=True)

        elif isinstance(error, commands.MissingPermissions):
            return await ctx.reply(f'Only people with **{error.missing_perms.join("**, **")}** permissions can run `{ctx.prefix}{ctx.command.name}`', private=True)

        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.reply(f'I need **{error.missing_perms.join("**, **")}** permissions in order to run `{ctx.prefix}{ctx.command.name}`', private=True)

        elif isinstance(error, commands.BadArgument):
            return await ctx.reply(guilded.utils.escape_mentions(str(error)), private=True)

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(f'You are missing a required argument: `{error.param.name}`', private=True)

        elif isinstance(error, guilded.Forbidden):
            msg = 'I am missing the required permissions to do that.'
            if error.raw_missing_permissions:
                msg += '\n' + ('\n'.join(error.raw_missing_permissions))

            return await ctx.reply(
                msg,
                private=True,
            )

        else:
            await ctx.reply('An unexpected error occurred.', private=True)
            print(f'Exception in command {ctx.command}:', file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def setup(bot: Bot):
    bot.add_cog(Main(bot))
    bot.add_cog(Errors(bot))
