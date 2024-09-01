from .. import logger

from disnake import Invite, Guild, Member, errors
from typing import Optional, Union
from disnake.ext.invitetracker.database.models import GuildModel, GuildInviteModel, UserModel, UserInvitedModel, UserInviteModel
from disnake.ext.commands import InteractionBot, Bot
from tortoise.exceptions import DoesNotExist
import traceback


class Database:
    def __init__(self, bot: Union[InteractionBot, Bot]) -> None:
        self.bot = bot

    async def _get_guild(self, guild_id: int) -> Optional[GuildModel]:
        """
        Get a GuildModel object from a code and a guild ID.

        :param guild_id: int: The guild ID.
        :return: Optional[GuildModel]: The GuildModel object or None if not found.
        """
        guild = await GuildModel.get_or_none(id=guild_id)
        if not guild:
            guild = await GuildModel.create(id=guild_id)
        return guild

    async def find_invite_in_guild(
        self, guild_id: int, code: str
    ) -> Optional[GuildInviteModel]:
        """
        Find an invite in a guild.

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
    
    async def find_invite_in_user(
        self, member_id: int, code: str
    ) -> Optional[GuildInviteModel]:
        user = await UserModel.get_or_none(id=member_id).prefetch_related("invited")

        if user is None:
            user = await UserModel.create(id=member_id)

        invite = await user.invites.filter(code=code).first()

        if invite is None:
            invite = await UserInviteModel.create(code=code)
            await user.invites.add(invite)

        return invite

    async def _load_invites(self) -> GuildModel:
        """Load all invites from a guild."""
        for guild in self.bot.guilds:
            try:
                for invite in await guild.invites():
                    data = await self.find_invite_in_guild(guild.id, invite.code)
                    data.uses = invite.uses
                    await data.save()
                    # guild = await self._get_guild(guild.id)
                    # data_invite = await GuildModel.get_invite(invite.code)
                    # data_invite.uses = invite.uses
                    logger.debug(
                        f"[+] [DB] Loaded invite {invite.code} from guild {guild.id}"
                    )

            except Exception as error:
                logger.error(
                    f"[x] [DB] Error while loading invites from guild {guild.id}: {traceback.format_exc()}"
                )

        logger.info("[+] [DB] Loaded all invites from guilds.")

        return data

    async def _add_guild(self, guild: GuildModel) -> GuildModel:
        """
        Add a guild to the cache.

        :param guild: disnake.Guild: New guild to add to the cache.
        :return: T: The updated cache.
        """
        try:
            for invite in await guild.invites():
                data = await self.find_invite_in_guild(guild.id, invite.code)
                data.uses = invite.uses
                await data.save()
                logger.debug(
                    f"[+] [DB] Added invite {invite.code} from guild {guild.id}"
                )

        except (errors.HTTPException, errors.Forbidden):
            logger.error(f"[x] [DB] Failed to add invites from guild {guild.id}")

        logger.info(f"[+] [DB] Added guild {guild.id} to the cache.")

        return data

    async def _remove_guild(self, guild: GuildModel) -> GuildModel:
        """
        Remove a guild from the cache.

        :param guild: disnake.Guild: The guild to remove from the cache.
        :return: T: The updated cache.
        """
        try:
            for invite in await guild.invites():
                data = await self._get_guild(guild.id)
                await GuildModel.delete(data)
        except KeyError:
            logger.error(f"[x] [DB] Failed to remove guild {guild.id} from the cache.")

        logger.debug(f"[+] [DB] Removed guild {guild.id} from the cache.")

        return data

    async def _create_invite(self, invite: Invite) -> GuildModel:
        """
        Create an invitation and add it to the cache.

        :param invite: disnake.Invite: The invite to create.
        :return: T: The updated cache.
        """
        data = await self.find_invite_in_guild(invite.guild.id, invite.code)
        data.uses = invite.uses
        await data.save()

        logger.info(
            f"[+] [DB] Created invite {invite.code} from guild {invite.guild.id}"
        )

        return data

    async def _delete_invite(self, invite: Invite) -> GuildModel:
        """
        Delete an invitation from the cache.

        :param invite: disnake.Invite: The invite to delete.
        :return: T: The updated cache.
        """
        data = await self.find_invite_in_guild(invite.guild.id, invite.code)
        await data.delete()
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
                    cached_invite = await self.find_invite_in_guild(
                        guild_id, invite_raw.code
                    )

                    logger.debug(f"[+] [DB] Found invite raw code: {invite_raw.code}")
                    logger.debug(
                        f"[+] [DB] Found invite cached code: {cached_invite.code}"
                    )

                    if invite_raw.uses > cached_invite.uses:
                        cached_invite.uses = invite_raw.uses
                        await cached_invite.save()
                        invite = invite_raw
                        logger.debug(
                            f"[+] [DB] Updated invite uses: {invite.code} ({invite.uses})"
                        )

                    # if invite_raw.code != cached_invite.code:
                    #     logger.warning(f"[!] Mismatch between DB code {cached_invite.code} and cache code {invite_raw.code}")

                except DoesNotExist:
                    logger.warning(
                        f"[x] [DB] Invite {invite_raw.code} not found in cache for guild {guild_id}"
                    )

        except Exception as e:
            logger.error(f"[x] [DB] An error occurred: {str(e)}")

        return invite
    
    async def get_from_invited_member(self, member: Member) -> Optional[Member]:
        """
        Получить участника, который пригласил данного участника.

        :param member: disnake.Member: Участник, для которого нужно найти пригласившего.
        :return: Optional[disnake.Member]: Участник, который пригласил или None, если не найден.
        """
        try:
            user = await UserModel.get_or_none(id=member.id).prefetch_related("invited")

            if user is None:
                logger.warning(f"[x] [DB] Пользователь {member.id} не найден в базе данных.")
                return None

            invite_entry = await user.invited.first()

            if invite_entry is None:
                logger.warning(f"[x] [DB] Приглашение для пользователя {member.id} не найдено.")
                return None

            inviting_user_invite = await UserInviteModel.get_or_none(code=invite_entry.code)
            
            if inviting_user_invite is None:
                logger.warning(f"[x] [DB] Пользователь, пригласивший через код {invite_entry.code}, не найден.")
                return None

            inviting_user = await UserModel.get_or_none(invited__code=invite_entry.code)

            if inviting_user is None:
                logger.warning(f"[x] [DB] Пользователь, использовавший код {invite_entry.code}, не найден.")
                return None

            inviting_member = member.guild.get_member(inviting_user.id)

            if inviting_member is None:
                logger.warning(f"[x] [DB] Участник с ID {inviting_user.id} не найден в гильдии.")
                return None

            return inviting_member

        except Exception as e:
            logger.error(f"[x] [DB] Ошибка при получении пригласившего участника: {str(e)}")
            return None
