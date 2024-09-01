import logging

import disnake
from disnake.ext import commands
from disnake.ext.invitetracker.tracker import InviteTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InviteTracker")

bot = commands.Bot(
    command_prefix="!",
    command_sync_flags=commands.CommandSyncFlags.all(),
    intents=disnake.Intents.all(),
)
bot.invite_tracker = InviteTracker(
    bot=bot, db_url="sqlite://invitetracker.sqlite3", use_db=True
)


@bot.event
async def on_ready() -> None:
    logger.info(f"Logged in as {bot.user.name}")


@bot.event
async def on_member_join(member: disnake.Member) -> None:
    await bot.invite_tracker.add_member(member)


@bot.event
async def on_member_remove(member: disnake.Member) -> None:
    logger.info(f"Member {member} left the guild {member.guild.name}")
    await bot.invite_tracker.delete_member(member)


@bot.slash_command(name="who_invited")
async def who_invited(interaction: disnake.ApplicationCommandInteraction):
    inviter = await bot.invite_tracker.get_inviter(
        member_id=interaction.user.id, guild=interaction.guild
    )
    if inviter:
        await interaction.response.send_message(f"You were invited by {inviter.name}.")
        logger.info(f"{interaction.user.name} was invited by {inviter.name}")
    else:
        await interaction.response.send_message("I couldn't find who invited you.")
        logger.warning(f"Could not find invite record for {interaction.user.name}")


@bot.slash_command(name="my_invites")
async def my_invites(interaction: disnake.ApplicationCommandInteraction):
    invited_members = await bot.invite_tracker.get_invited_members(
        user_id=interaction.user.id, guild=interaction.guild
    )
    if invited_members:
        member_names = [str(member.name) for member in invited_members]
        await interaction.response.send_message(
            "You invited the following members:\n" + "\n".join(member_names)
        )
        logger.info(
            f"{interaction.user.name} has invited {len(invited_members)} members"
        )
    else:
        await interaction.response.send_message("You haven't invited anyone yet.")
        logger.warning(f"No invites found for {interaction.user.name}")


bot.run("TOKEN")
