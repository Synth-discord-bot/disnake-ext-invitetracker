import collections

from typing import Optional, Union, TypeVar

from disnake import Invite, Guild, Member, errors
from disnake.ext.commands import InteractionBot, Bot

from ..logger import logger


class InviteCache:
    def __init__(self, debug: bool = False) -> None:
        self._cache: dict[int, dict[str, Invite]] = collections.defaultdict()
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
        invites = self._cache.get(guild_id, None)
        self._debug(f"Found {len(invites)} invites in cache in guild {guild_id}")
        return self._cache.get(guild_id, None)

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
        self._debug(f"Updated cache with {len(invites)} invites in guild {guild_id}")
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

        return

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
