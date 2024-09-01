from collections import defaultdict

# from disnake.ext.invitetracker.tracker import InviteTracker
from typing import Optional, Union

from disnake import Invite, Guild, Member, errors
from disnake.ext.commands import InteractionBot, Bot

from disnake.ext.invitetracker import logger, T


class Cache:
    def __init__(self, bot: Union[InteractionBot, Bot], cache) -> None:
        self.bot = bot
        self.cache = cache

    async def _load_invites(self) -> T:
        """Load all invites from a guild."""
        for guild in self.bot.guilds:
            try:
                self.cache[guild.id] = {}

                for invite in await guild.invites():
                    self.cache[guild.id][invite.code] = invite
                    logger.debug(
                        f"[+] [CACHE] Loaded invite {invite.code} from guild {guild.id}"
                    )

            except Exception as error:
                logger.error(
                    f"[-] [CACHE] Error while loading invites from guild {guild.id}: {error}"
                )

        logger.info("[+] [CACHE] Loaded all invites from guilds.")

        return self.cache

    async def _add_guild(self, guild: Guild) -> T:
        """
        Add a guild to the cache.

        :param guild: disnake.Guild: New guild to add to the cache.
        :return: T: The updated cache.
        """
        self.cache[guild.id] = {}

        try:
            for invite in await guild.invites():
                self.cache[guild.id][invite.code] = invite
                logger.debug(
                    f"[+] [CACHE] Added invite {invite.code} from guild {guild.id}"
                )

        except (errors.HTTPException, errors.Forbidden):
            logger.error(f"[x] [CACHE] Failed to add invites from guild {guild.id}")

        logger.info(f"[+] [CACHE] Added guild {guild.id} to the cache.")

        return self.cache

    async def _remove_guild(self, guild: Guild) -> T:
        """
        Remove a guild from the cache.

        :param guild: disnake.Guild: The guild to remove from the cache.
        :return: T: The updated cache.
        """
        try:
            self.cache.pop(guild.id)
        except KeyError:
            logger.error(
                f"[x] [CACHE] Failed to remove guild {guild.id} from the cache."
            )

        logger.debug(f"[+] [CACHE] Removed guild {guild.id} from the cache.")

        return self.cache

    async def _create_invite(self, invite: Invite) -> T:
        """
        Create an invitation and add it to the cache.

        :param invite: disnake.Invite: The invite to create.
        :return: T: The updated cache.
        """
        if invite.guild.id not in self.cache.keys():
            self.cache[invite.guild.id] = {}

        self.cache[invite.guild.id][invite.code] = invite

        logger.info(
            f"[+] [CACHE] Created invite {invite.code} from guild {invite.guild.id}"
        )

        return self.cache

    async def _delete_invite(self, invite: Invite) -> T:
        """
        Delete an invitation from the cache.

        :param invite: disnake.Invite: The invite to delete.
        :return: T: The updated cache.
        """
        if invite.guild.id not in self.cache:
            return self.cache

        if invite.code in self.cache[invite.guild.id]:
            self.cache[invite.guild.id].pop(invite.code)
            logger.info(
                f"[+] [CACHE] Deleted invite {invite.code} from guild {invite.guild.id}"
            )

        return self.cache

    async def get_invite(self, member: Member) -> Optional[Invite]:
        """
        Get an invitation author from a member.

        :param member: disnake.Member: The member to get the invite from.
        :return: Optional[disnake.Invite]: The invite or None if not found.
        """
        guild_cache = self.cache.get(member.guild.id)
        invite = None

        if not guild_cache:
            logger.error(f"[x] [CACHE] Guild {member.guild.id} not found in the cache.")
            return None

        for invite_raw in await member.guild.invites():
            cached_invite = guild_cache.get(invite_raw.code)

            if cached_invite and invite_raw.uses > cached_invite.uses:
                cached_invite.uses = invite_raw.uses
                invite = invite_raw

                logger.debug(
                    f"[+] [CACHE] Found invite {invite.code} from guild {member.guild.id}"
                )
                break

        return invite


class InviteCache:
    def __init__(self, debug: bool = False) -> None:
        self._cache: dict[int, dict[str, Invite]] = defaultdict()
        self.debug = debug
        self.logger = logger

    def _debug(self, msg: str) -> None:
        if self.debug:
            self.logger.info(msg)

    @property
    def cache(self) -> dict[int, dict[str, Invite]]:
        return self._cache

    def get(self, guild_id) -> Optional[dict[str, Invite]]:
        """Get the invites from the cache.

        Parameters
        ----------
        guild_id: int
            The ID of the guild

        Returns
        -------
        Invites from the cache
        """
        invites = self._cache.get(guild_id)
        if invites is None:
            self._debug(f"No invites in cache in guild {guild_id}")
        else:
            self._debug(f"Found {len(invites)} invites in cache in guild {guild_id}")
        return invites

    def update(
        self, guild_id: int, invites: Union[dict[str, Invite], Invite]
    ) -> dict[str, Invite]:
        """Update the cache with new invites.

        Parameters
        ----------
        guild_id: int
            The ID of the guild
        invites: dict[str, disnake.Invite] or disnake.Invite
            The new invites to add

        Returns
        -------
        Updated cache
        """
        if isinstance(invites, Invite):
            old_invites = self._cache.get(guild_id, {})
            old_invites[invites.code] = invites
            invites = old_invites

        self._cache[guild_id] = invites
        self._debug(
            f"Updated cache with {len(invites or [])} invites in guild {guild_id}"
        )
        return self._cache.get(guild_id, {})

    def delete_invite(
        self, guild_id: int, invite_code: Union[Invite, str]
    ) -> Optional[Invite]:
        """Delete an invitation from the cache.

        Parameters
        ----------
        guild_id: int
            The ID of the guild
        invite_code: str
            The invite code

        Returns
        -------
        Deleted invite (disnake.Invite) from the cache
        """
        if isinstance(invite_code, Invite):
            invite_code = invite_code.code

        if guild_id in self._cache and invite_code in self._cache[guild_id]:
            old_value = self._cache[guild_id][invite_code]
            del self._cache[guild_id][invite_code]
            self._debug(f"Deleted invite {invite_code} from guild {guild_id}")
            return old_value

        self._debug(f"Invite {invite_code} not found in guild {guild_id}")
        return None

    def add_invite(self, guild_id: int, invite: Invite) -> Invite:
        """Add an invitation to the cache.

        Parameters
        ----------
        guild_id: int
            The ID of the guild
        invite: disnake.Invite
            The invite to add

        Returns
        -------
        Added invite (disnake.Invite) to the cache
        """
        if guild_id not in self._cache:
            self._cache[guild_id] = {}
            self._debug(f"initialized cache for guild {guild_id}")
        self._cache[guild_id][invite.code] = invite
        self._debug(f"Added invite {invite.code} to the guild {guild_id} cache")
        return invite

    async def update_invites_cache(self, guilds: list[Guild]) -> None:
        """Synchronize the cache with all guild invites.

        Parameters
        ----------
        guilds: list[disnake.Guild]
            The guilds to update the cache with
        """
        logger.info("[~] [CACHE] Updating invites cache...")

        for guild in guilds:
            invites = {invite.code: invite for invite in await guild.invites()}
            self.update(guild.id, invites)

        logger.info("[+] [CACHE] Updated invites cache.")
        return
