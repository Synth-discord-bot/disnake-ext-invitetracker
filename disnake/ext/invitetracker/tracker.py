from typing import Union

from disnake.ext.invitetracker.util.cache import Cache
from disnake.ext.invitetracker.util.database import Database

from .database import init_database, close_database
from . import T, logger
from disnake import Invite, Member
from disnake.ext.commands import InteractionBot, Bot


class InviteTracker:
    def __init__(
        self,
        bot: Union[InteractionBot, Bot],
        db_url: str,
        work: bool = True,
        use_db: bool = False,
        use_cache: bool = True,
    ) -> None:
        self.bot: Union[InteractionBot, Bot] = bot
        self.db_url = db_url
        self.use_db = use_db
        self.work: bool = work
        self.cache: T = {}
        self.use_cache = use_cache

        if self.work:
            if self.use_db:
                self.bot.add_listener(self._load_database, "on_connect")
                self.bot.add_listener(self._unload_database, "on_disconnect")

                self.database_instance = Database(self.bot)
                self.bot.add_listener(self.database_instance._load_invites, "on_ready")
                self.bot.add_listener(
                    self.database_instance._add_guild, "on_guild_join"
                )
                self.bot.add_listener(
                    self.database_instance._remove_guild, "on_guild_remove"
                )
                self.bot.add_listener(
                    self.database_instance._create_invite, "on_invite_create"
                )
                self.bot.add_listener(
                    self.database_instance._delete_invite, "on_invite_delete"
                )

            if self.use_cache:
                self.cache_instance = Cache(self.bot, self.cache)
                self.bot.add_listener(self.cache_instance._load_invites, "on_ready")
                self.bot.add_listener(self.cache_instance._add_guild, "on_guild_join")
                self.bot.add_listener(
                    self.cache_instance._remove_guild, "on_guild_remove"
                )
                self.bot.add_listener(
                    self.cache_instance._create_invite, "on_invite_create"
                )
                self.bot.add_listener(
                    self.cache_instance._delete_invite, "on_invite_delete"
                )
                logger.info("[+] Cache initialized")

    async def _load_database(self) -> None:
        """Load the database."""
        await init_database(db_url=self.db_url)

    async def _unload_database(self) -> None:
        """Unload the database."""
        await close_database()

    async def get_invite_cache(self, member: Member) -> Invite:
        """Get the invite cache."""
        if self.use_cache:
            return await self.cache_instance.get_invite(member)
        return None

    async def get_invite_db(self, member: Member) -> Invite:
        """Get the invite database."""
        if self.use_db:
            return await self.database_instance.get_invite(member)
        return None
