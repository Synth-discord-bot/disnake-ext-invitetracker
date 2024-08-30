from .. import logger

from disnake import Invite, Guild, Member, errors
from typing import Optional, Union
from ..database.models import Tracker
from disnake.ext.commands import InteractionBot, Bot
from tortoise.expressions import Q
from tortoise.exceptions import DoesNotExist


class Database:
    def __init__(self, bot: Union[InteractionBot, Bot]) -> None:
        self.bot = bot

    async def get_data(self, code: str, guild_id: int) -> Optional[Tracker]:
        """
        Get a Tracker object from a code and a guild ID.

        :param code: str: The invite code.
        :param guild_id: int: The guild ID.
        :return: Optional[Tracker]: The Tracker object or None if not found.
        """
        result = await Tracker.get_or_none(code=code, guild_id=guild_id)

        if not result:
            result = await Tracker.create(code=code, guild_id=guild_id)
        return result

    async def _load_invites(self) -> Tracker:
        """Load all invites from a guild."""
        for guild in self.bot.guilds:
            try:
                for invite in await guild.invites():
                    data = await self.get_data(invite.code, guild.id)
                    data.uses = invite.uses
                    logger.debug(
                        f"[+] [DB] Loaded invite {invite.code} from guild {guild.id}"
                    )

            except Exception as error:
                logger.error(
                    f"[x] [DB] Error while loading invites from guild {guild.id}: {error}"
                )

        logger.info("[+] [DB] Loaded all invites from guilds.")

        return data

    async def _add_guild(self, guild: Guild) -> Tracker:
        """
        Add a guild to the cache.

        :param guild: disnake.Guild: New guild to add to the cache.
        :return: T: The updated cache.
        """
        try:
            for invite in await guild.invites():
                data = await self.get_data(invite.code, guild.id)
                data.uses = invite.uses
                await data.save()
                logger.debug(
                    f"[+] [DB] Added invite {invite.code} from guild {guild.id}"
                )

        except (errors.HTTPException, errors.Forbidden):
            logger.error(f"[x] [DB] Failed to add invites from guild {guild.id}")

        logger.info(f"[+] [DB] Added guild {guild.id} to the cache.")

        return data

    async def _remove_guild(self, guild: Guild) -> Tracker:
        """
        Remove a guild from the cache.

        :param guild: disnake.Guild: The guild to remove from the cache.
        :return: T: The updated cache.
        """
        try:
            for invite in await guild.invites():
                data = await self.get_data(invite.code, guild.id)
                await Tracker.delete(data)
        except KeyError:
            logger.error(f"[x] [DB] Failed to remove guild {guild.id} from the cache.")

        logger.debug(f"[+] [DB] Removed guild {guild.id} from the cache.")

        return data

    async def _create_invite(self, invite: Invite) -> Tracker:
        """
        Create an invitation and add it to the cache.

        :param invite: disnake.Invite: The invite to create.
        :return: T: The updated cache.
        """
        data = await self.get_data(invite.code, invite.guild.id)
        data.uses = invite.uses
        await data.save()

        logger.info(
            f"[+] [DB] Created invite {invite.code} from guild {invite.guild.id}"
        )

        return self.cache

    async def _delete_invite(self, invite: Invite) -> Tracker:
        """
        Delete an invitation from the cache.

        :param invite: disnake.Invite: The invite to delete.
        :return: T: The updated cache.
        """
        data = await Tracker.filter(code=invite.code, guild_id=invite.guild.id).first()
        if invite.code not in data:
            logger.error(
                f"[x] [DB] Invite {invite.code} not found in guild {invite.guild.id}."
            )
            return data

        if invite.code in data:
            await Tracker.delete(data)
            logger.info(
                f"[+] [DB] Deleted invite {invite.code} from guild {invite.guild.id}"
            )

        return data

    async def get_invite(self, member: Member) -> Optional[Invite]:
        guild_id = member.guild.id
        invite = None

        try:
            for invite_raw in await member.guild.invites():
                try:
                    logger.debug(f"[+] [DB] Found invite raw code: {invite_raw.code}")
                    cached_invite = await Tracker.get(Q(code=invite_raw.code) & Q(guild_id=guild_id))
                    logger.debug(f"[+] [DB] Found invite cached code: {cached_invite.code}")

                    if invite_raw.uses > cached_invite.uses:
                        cached_invite.uses = invite_raw.uses
                        await cached_invite.save()
                        invite = invite_raw
                        logger.debug(f"[+] [DB] Updated invite uses: {invite.code} ({invite.uses})")

                    # if invite_raw.code != cached_invite.code:
                    #     logger.warning(f"[!] Mismatch between DB code {cached_invite.code} and cache code {invite_raw.code}")

                except DoesNotExist:
                    logger.warning(f"[x] [DB] Invite {invite_raw.code} not found in cache for guild {guild_id}")

        except Exception as e:
            logger.error(f"[x] [DB] An error occurred: {str(e)}")

        return invite
