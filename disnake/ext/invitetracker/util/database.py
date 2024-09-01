from typing import Optional, Union

from async_lru import alru_cache
from disnake import Guild, Invite, Member, errors
from disnake.ext.commands import InteractionBot, Bot
from ..database.models import (
    GuildModel,
    GuildInviteModel,
    UserInvitedModel,
)

from .. import logger
from ..util.cache import InviteCache


class Database:
    def __init__(self, bot: Union[InteractionBot, Bot], debug: bool = False) -> None:
        self.bot = bot
        self.invite_cache = InviteCache(debug=debug)

    async def _get_invite_for_member(self, member: Member) -> Optional[Invite]:
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
    ) -> Optional[GuildInviteModel]:
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
    async def get_guild_invites(self, guild: Guild) -> Optional[list[Invite]]:
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

    # async def del(self, guild_id: int = None, member_id: Union[disnake.Member, int] = None) -> None:
    #     """
    #     Delete an invitation from the database.
    #
    #     Parameters
    #     ----------
    #     guild_id: int
    #         The ID of the guild
    #     code: str
    #         The code of the invite
    #     """
    #     logger.info(f"Deleting invite {} from the database")
    #     # await UserInvitedModel.filter(guild_id=guild_id, invite_code=code).delete()
    #     await UserInvitedModel.filter(id=member.id, guild_id=member.guild.id).delete()
    #     logger.info(f"Invite {code} deleted from the database")

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

    # async def _get_guild(self, guild_id: int) -> Optional[GuildModel]:
    #     """
    #     Get a GuildModel object from a code and a guild ID.
    #
    #     :param guild_id: int: The guild ID.
    #     :return: Optional[GuildModel]: The GuildModel object or None if not found.
    #     """
    #     guild = await GuildModel.get_or_none(id=guild_id)
    #     if not guild:
    #         guild = await GuildModel.create(id=guild_id)
    #     return guild
    #
    # async def find_invite_in_guild(
    #     self, guild_id: int, code: str
    # ) -> Optional[GuildInviteModel]:
    #     """
    #     Find an invite in a guild.
    #
    #     :param guild_id: int: The guild ID.
    #     :param code: str: The invite code.
    #     :return: Optional[GuildInviteModel]: The GuildInviteModel object or None if not found.
    #     """
    #     guild = await GuildModel.get_or_none(id=guild_id).prefetch_related("invites")
    #
    #     if guild is None:
    #         guild = await GuildModel.create(id=guild_id)
    #
    #     invite = await guild.invites.filter(code=code).first()
    #
    #     if invite is None:
    #         invite = await GuildInviteModel.create(code=code, uses=0)
    #         await guild.invites.add(invite)
    #
    #     return invite
    #
    # async def find_invite_in_user(
    #     self, member_id: int, code: str
    # ) -> Optional[GuildInviteModel]:
    #     user = await UserModel.get_or_none(id=member_id).prefetch_related("invited")
    #
    #     if user is None:
    #         user = await UserModel.create(id=member_id)
    #
    #     invite = await user.invites.filter(code=code).first()
    #
    #     if invite is None:
    #         invite = await UserInviteModel.create(code=code)
    #         await user.invites.add(invite)
    #
    #     return invite
    #
    # async def _load_invites(self) -> GuildModel:
    #     """Load all invites from a guild."""
    #     for guild in self.bot.guilds:
    #         try:
    #             for invite in await guild.invites():
    #                 data = await self.find_invite_in_guild(guild.id, invite.code)
    #                 data.uses = invite.uses
    #                 await data.save()
    #                 # guild = await self._get_guild(guild.id)
    #                 # data_invite = await GuildModel.get_invite(invite.code)
    #                 # data_invite.uses = invite.uses
    #                 logger.debug(
    #                     f"[+] [DB] Loaded invite {invite.code} from guild {guild.id}"
    #                 )
    #
    #         except Exception as error:
    #             logger.error(
    #                 f"[x] [DB] Error while loading invites from guild {guild.id}: {traceback.format_exc()}"
    #             )
    #
    #     logger.info("[+] [DB] Loaded all invites from guilds.")
    #
    #     return data
    #
    # async def _add_guild(self, guild: GuildModel) -> GuildModel:
    #     """
    #     Add a guild to the cache.
    #
    #     :param guild: disnake.Guild: New guild to add to the cache.
    #     :return: T: The updated cache.
    #     """
    #     try:
    #         for invite in await guild.invites():
    #             data = await self.find_invite_in_guild(guild.id, invite.code)
    #             data.uses = invite.uses
    #             await data.save()
    #             logger.debug(
    #                 f"[+] [DB] Added invite {invite.code} from guild {guild.id}"
    #             )
    #
    #     except (errors.HTTPException, errors.Forbidden):
    #         logger.error(f"[x] [DB] Failed to add invites from guild {guild.id}")
    #
    #     logger.info(f"[+] [DB] Added guild {guild.id} to the cache.")
    #
    #     return data
    #
    # async def _remove_guild(self, guild: GuildModel) -> GuildModel:
    #     """
    #     Remove a guild from the cache.
    #
    #     :param guild: disnake.Guild: The guild to remove from the cache.
    #     :return: T: The updated cache.
    #     """
    #     try:
    #         for invite in await guild.invites():
    #             data = await self._get_guild(guild.id)
    #             await GuildModel.delete(data)
    #     except KeyError:
    #         logger.error(f"[x] [DB] Failed to remove guild {guild.id} from the cache.")
    #
    #     logger.debug(f"[+] [DB] Removed guild {guild.id} from the cache.")
    #
    #     return data
    #
    # async def _create_invite(self, invite: Invite) -> GuildModel:
    #     """
    #     Create an invitation and add it to the cache.
    #
    #     :param invite: disnake.Invite: The invite to create.
    #     :return: T: The updated cache.
    #     """
    #     data = await self.find_invite_in_guild(invite.guild.id, invite.code)
    #     data.uses = invite.uses
    #     await data.save()
    #
    #     logger.info(
    #         f"[+] [DB] Created invite {invite.code} from guild {invite.guild.id}"
    #     )
    #
    #     return data
    #
    # async def _delete_invite(self, invite: Invite) -> GuildModel:
    #     """
    #     Delete an invitation from the cache.
    #
    #     :param invite: disnake.Invite: The invite to delete.
    #     :return: T: The updated cache.
    #     """
    #     data = await self.find_invite_in_guild(invite.guild.id, invite.code)
    #     await data.delete()
    #     logger.info(
    #         f"[+] [DB] Deleted invite {invite.code} from guild {invite.guild.id}"
    #     )
    #
    #     return data
    #
    # async def get_invite(self, member: Member) -> Optional[Invite]:
    #     guild_id = member.guild.id
    #     invite = None
    #
    #     try:
    #         for invite_raw in await member.guild.invites():
    #             try:
    #                 cached_invite = await self.find_invite_in_guild(
    #                     guild_id, invite_raw.code
    #                 )
    #
    #                 logger.debug(f"[+] [DB] Found invite raw code: {invite_raw.code}")
    #                 logger.debug(
    #                     f"[+] [DB] Found invite cached code: {cached_invite.code}"
    #                 )
    #
    #                 if invite_raw.uses > cached_invite.uses:
    #                     cached_invite.uses = invite_raw.uses
    #                     await cached_invite.save()
    #                     invite = invite_raw
    #                     logger.debug(
    #                         f"[+] [DB] Updated invite uses: {invite.code} ({invite.uses})"
    #                     )
    #
    #                 # if invite_raw.code != cached_invite.code:
    #                 #     logger.warning(f"[!] Mismatch between DB code {cached_invite.code} and cache code {invite_raw.code}")
    #
    #             except DoesNotExist:
    #                 logger.warning(
    #                     f"[x] [DB] Invite {invite_raw.code} not found in cache for guild {guild_id}"
    #                 )
    #
    #     except Exception as e:
    #         logger.error(f"[x] [DB] An error occurred: {str(e)}")
    #
    #     return invite
    #
    # async def get_from_invited_member(self, member: Member) -> Optional[Member]:
    #     """
    #     Получить участника, который пригласил данного участника.
    #
    #     :param member: disnake.Member: Участник, для которого нужно найти пригласившего.
    #     :return: Optional[disnake.Member]: Участник, который пригласил или None, если не найден.
    #     """
    #     try:
    #         # Найти информацию о пользователе, который был приглашен
    #         invited_entry = await UserInvitedModel.get_or_none(id=member.id)
    #
    #         if not invited_entry:
    #             logger.warning(
    #                 f"[x] [DB] Пользователь {member.id} не найден в базе данных."
    #             )
    #
    #             # Попробуем получить приглашение из кеша
    #             cache_invite = await self.get_invite(member)
    #             # cache_invite = await self.cache_instance.get_invite(member)
    #             if not cache_invite:
    #                 logger.warning(
    #                     f"[x] [CACHE] Не удалось найти инвайт для пользователя {member.id}."
    #                 )
    #                 return None
    #
    #             # Записываем пользователя в базу данных
    #             invited_entry = await UserInvitedModel.create(
    #                 id=member.id, code=cache_invite.code, joined_at=member.joined_at
    #             )
    #             logger.info(
    #                 f"[+] [DB] Пользователь {member.id} добавлен в базу данных с инвайтом {cache_invite.code}."
    #             )
    #
    #         # Найти приглашение по коду, через которое участник присоединился
    #         invite = await UserInviteModel.get_or_none(code=invited_entry.code)
    #
    #         if not invite:
    #             logger.warning(
    #                 f"[x] [DB] Приглашение с кодом {invited_entry.code} не найдено."
    #             )
    #             return None
    #
    #         # Найти пригласившего участника
    #         inviting_user = await UserModel.get_or_none(id=invite.invited_id)
    #
    #         if not inviting_user:
    #             logger.warning(
    #                 f"[x] [DB] Пользователь, использовавший код {invite.code}, не найден."
    #             )
    #             return None
    #
    #         inviting_member = member.guild.get_member(inviting_user.id)
    #
    #         if not inviting_member:
    #             logger.warning(
    #                 f"[x] [DB] Участник с ID {inviting_user.id} не найден в гильдии."
    #             )
    #             return None
    #
    #         return inviting_member
    #
    #     except Exception as e:
    #         logger.error(
    #             f"[x] [DB] Ошибка при получении пригласившего участника: {str(e)}"
    #         )
    #         return None
