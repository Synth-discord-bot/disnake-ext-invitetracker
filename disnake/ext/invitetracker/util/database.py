import typing

from async_lru import alru_cache
from disnake import Guild, Invite, Member, errors
from disnake.ext.commands import InteractionBot, Bot
from ..database.models import (
    GuildModel,
    GuildInviteModel,
    UserInvitedModel,
)

from ..logger import logger
from ..util.cache import InviteCache


class Database:
    def __init__(
        self, bot: typing.Union[InteractionBot, Bot], debug: bool = False
    ) -> None:
        self.bot = bot
        self.invite_cache = InviteCache(debug=debug)

    async def _get_invite_for_member(self, member: Member) -> typing.Optional[Invite]:
        logger.info(f"Checking invites for member {member}")
        current_invites = await member.guild.invites()

        old_invites = self.invite_cache.get(member.guild.id)

        for invite in current_invites:
            old_invite = old_invites.get(invite.code)
            if old_invite and invite.uses > old_invite.uses:
                self.invite_cache.add_invite(member.guild.id, invite)
                logger.info(f"Found invite {invite.code} for member {member}")
                return invite

        logger.warning(f"No matching invite found for member {member}")
        return

    async def load_invites_to_cache(self) -> None:
        """
        Load all invites from all guilds in the cache.

        This function is used to pre-cache all invites when the bot is ready.
        """

        await self.invite_cache.update_invites_cache(self.bot.guilds)

    @staticmethod
    async def find_invite_in_guild(
        guild_id: int, code: str
    ) -> typing.Optional[GuildInviteModel]:
        """
        Find an invitation in a guild (Database only)

        :param guild_id: int: The guild ID.
        :param code: str: The invite code.
        :return: Optional[GuildInviteModel]: The GuildInviteModel object or None if not found.
        """
        guild = await GuildModel.get_or_none(id=guild_id).prefetch_related("invites")

        if guild is None:
            guild = await GuildModel.create(id=guild_id)

        invite = await guild.invites.filter(code=code).first()

        if invite is None:
            invite = await GuildInviteModel.create(code=code, uses=0)
            await guild.invites.add(invite)

        return invite

    @alru_cache(maxsize=None)
    async def get_guild_invites(self, guild: Guild) -> typing.Optional[list[Invite]]:
        """
        Get all invites from a guild.

        Parameters
        ----------
        guild: disnake.Guild
            The guild to get invites from

        Returns
        -------
        list[disnake.Invite]
            A list of all invites in the guild
        """
        try:
            invites = await guild.invites()
            return invites
        except (errors.HTTPException, errors.Forbidden):
            logger.error(
                f"[x] Failed to get invites from guild {guild.id} due to permission error(s)"
            )
            return None

    async def _add_invs_to_db(self, guild: Guild) -> None:
        if not (invites := await self.get_guild_invites(guild)):
            return

        for invite in invites:
            data = await self.find_invite_in_guild(guild.id, invite.code)
            data.uses = invite.uses
            await data.save()
            logger.debug(f"[+] [DB] Added invite {invite.code} from guild {guild.id}")

            logger.info(f"[+] [DB] Added guild {guild.id} to the cache.")

    async def add_new_guild_invites(self, guild: Guild) -> None:
        """
        Add new invites from a new guild to the cache.

        Parameters
        ----------
        guild: disnake.Guild
            The guild to add invites from
        """
        # await self.([guild])
        await self._add_invs_to_db(guild)

    async def remove_guild_invites(self, guild: Guild) -> None:
        """
        Remove invites from a guild from the cache.

        Parameters
        ----------
        guild: disnake.Guild
            The guild to remove invites from
        """
        if not (invites := await self.get_guild_invites(guild)):
            return

        logger.info(f"[~] [CACHE] Removing guild {guild.id} from the cache")
        for invite in invites:
            self.invite_cache.delete_invite(guild.id, invite.code)
        del self.invite_cache.cache[guild.id]
        logger.info(f"[+] [CACHE] Removed guild {guild.id} from the cache")

        await GuildModel.filter(id=guild.id).delete()
        logger.info(f"[+] [DB] Removed guild {guild.id} from the database")

    async def add_invite(self, invite: Invite) -> GuildModel:
        """
        Add an invitation to the database.

        Parameters
        ----------
        invite: disnake.Invite
            The invite which was used to join the guild

        Returns
        -------
        UserInvitedModel
            The newly created or existing UserInvitedModel instance
        """
        logger.info(f"Invite created: {invite.code} in guild {invite.guild.name}")
        self.invite_cache.add_invite(invite.guild.id, invite)

        guild_model, created = await GuildModel.get_or_create(id=invite.guild.id)
        invite_model, created = await GuildInviteModel.get_or_create(code=invite.code)

        await guild_model.invites.add(invite_model)
        logger.info(
            f"Invite {invite.code} {'created' if created else 'added'} to the database."
        )
        return guild_model

    async def delete_invite(self, invite: Invite) -> None:
        """
        Delete an invitation from the database.

        Parameters
        ----------
        invite: disnake.Invite
            The invite to delete
        """
        logger.info(f"Deleting invite {invite.code} from the database")
        self.invite_cache.delete_invite(invite.guild.id, invite.code)
        await UserInvitedModel.filter(invite_code=invite.code).delete()
        logger.info(f"Invite {invite.code} deleted from the database")

    async def add_member(self, member: Member) -> None:
        """
        Add a member to the database.

        Parameters
        ----------
        member: disnake.Member
            The member to add to the database
        """
        logger.info(f"Member {member} joined to the guild {member.guild.name}")
        invite = await self._get_invite_for_member(member)

        if not invite:
            logger.warning(f"No invite found for member {member}")
            return

        await UserInvitedModel.create(
            id=member.id,
            guild_id=member.guild.id,
            invite_code=invite.code,
            joined_at=member.joined_at,
            inviter_id=invite.inviter.id if invite.inviter else None,
        )

        logger.info(f"Invite {invite.code} recorded for member {member}")

    @staticmethod
    async def delete_member(member: Member) -> None:
        """
        Delete a member from the database.

        Parameters
        ----------
        member: disnake.Member
            The member to delete from the database
        """
        result = await UserInvitedModel.filter(
            id=member.id, guild_id=member.guild.id
        ).first()
        if result:
            logger.info(
                f"Deleting member {member.name} from the invite {result.invite_code} database"
            )
            await result.delete()

        logger.info(f"Member {member.name} deleted from the database")
