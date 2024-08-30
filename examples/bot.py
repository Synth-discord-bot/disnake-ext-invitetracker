from os import getenv
import disnake
from disnake.ext import commands
from disnake.ext.invitetracker.tracker import InviteTracker
from disnake.ext.invitetracker.logger.logger import logger

bot = commands.InteractionBot(intents=disnake.Intents.all(), reload=True)
invite = InviteTracker(db_url="sqlite://invitetracker.sqlite3", bot=bot, use_db=True)


@bot.event
async def on_member_join(member: disnake.Member):
    original_invite: disnake.Invite = await invite.get_invite_cache(member)
    logger.info(f"[+] [CACHE] {member} joined using {original_invite.code}")
    original_invite: disnake.Invite = await invite.get_invite_db(member)
    logger.info(f"[+] [DB] {member} joined using {original_invite.code}")

bot.run("TOKEN")
