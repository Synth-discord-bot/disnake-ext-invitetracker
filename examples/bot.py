import disnake
from disnake.ext import commands
from disnake.ext.invitetracker.tracker import InviteTracker
from disnake.ext.invitetracker.logger.logger import logger

bot = commands.InteractionBot(intents=disnake.Intents.all(), reload=True)
invite = InviteTracker(db_url="sqlite://invitetracker.sqlite3", bot=bot, use_db=True)


@bot.event
async def on_member_join(member: disnake.Member):
    cache_invite: disnake.Invite = await invite.get_invite_cache(member)
    if cache_invite:
        logger.info(f"[+] [CACHE] {member} joined using {cache_invite.code}")
    db_invite: disnake.Member = await invite.get_from_invite_db(member)
    if db_invite:
        logger.info(f"[+] [DB] {member} joined using {db_invite}")


bot.run("TOKEN")
