from typing import Union

from async_lru import alru_cache
from disnake import Guild, Member
from disnake.ext.commands import InteractionBot, Bot

from .database import init_database, close_database
from .database.models import UserInvitedModel
from .util.database import Database


class InviteTracker:

    def __init__(
        self,
        bot: Union[InteractionBot, Bot],
        db_url: str,
        background: bool = True,
        initialize_db: bool = True,
        use_cache: bool = True,
        debug: bool = False,
    ) -> None:
        """
        Initialize the InviteTracker.

        :param bot: The bot instance.
        :type bot: Union[InteractionBot, Bot]
        :param db_url: The database URL to use.
        :type db_url: Str
        :param background: Run the invite tracker tasks in the background.
        :type background: Bool
        :param initialize_db: Initialize the database during startup.

        **TIP**
        - If you set `background` to True, you must initialize the process of updating cache manually.

        **WARNING:** *IF YOU ARE USING CUSTOM MODELS IN YOUR DATABASE, YOU MUST INITIALIZE THIS MODEL MANUALLY:*

        *disnake.ext.invitetracker.database.models.tracker*

        For example::

            Async def init_database():
                logger.info("# Initializing database...")
                await Tortoise.init(
                    db_url=settings.DATABASE_URL,
                    modules={"models": ["your_module.models", "disnake.ext.invitetracker.database.models.__init__"]},
                )
                await Tortoise.generate_schemas()
                logger.info("# Database initialized")

        *OTHERWISE YOU WILL BREAK YOUR DATABASE INITIALIZATION*

        *IF YOU ARE NOT USING CUSTOM MODELS, SET PARAM* `initialize_db` *TO True*

        :type initialize_db: Bool
        :param use_cache: Cache the invites in dictionaries for faster lookups.
        :type use_cache: Bool
        :param debug: Enable debug mode.
        :type debug: Bool
        """

        self.bot: Union[InteractionBot, Bot] = bot
        self.db_url: str = db_url
        self.use_cache: bool = use_cache
        self.initialize_db: bool = initialize_db
        self.background: bool = background
        self.debug = debug

        if self.initialize_db:
            self.bot.loop.create_task(self._load_database())
            self.bot.add_listener(self._unload_database, "on_disconnect")

        self.database_instance = Database(self.bot, debug=self.debug)

        if self.background:
            # self.bot.add_listener(self._load_database, "on_connect")
            # self.bot.add_listener(self._unload_database, "on_disconnect")

            self.bot.loop.create_task(self.database_instance.load_invites_to_cache())

            # self.bot.add_listener(
            # self.database_instance.load_invites_to_cache, "on_ready"
            # )

            self.bot.add_listener(
                self.database_instance.add_new_guild_invites, "on_guild_join"
            )
            self.bot.add_listener(
                self.database_instance.remove_guild_invites, "on_guild_remove"
            )
            self.bot.add_listener(self.database_instance.add_invite, "on_invite_create")
            self.bot.add_listener(
                self.database_instance.delete_invite, "on_invite_delete"
            )

    async def _load_database(self) -> None:
        """Load the database."""
        await init_database(db_url=self.db_url)
        # await init_database()

    @staticmethod
    async def _unload_database() -> None:
        """Unload the database."""
        await close_database()

    @alru_cache(maxsize=1000)
    async def get_inviter(self, member_id: int, guild: Guild):
        user_invited = await UserInvitedModel.get_or_none(
            id=member_id, guild_id=guild.id
        )
        if user_invited and user_invited.inviter_id:
            return await guild.fetch_member(user_invited.inviter_id)

        return None

    @alru_cache(maxsize=1000)
    async def get_invited_members(self, user_id: int, guild: Guild):
        invites = await UserInvitedModel.filter(
            inviter_id=user_id, guild_id=guild.id
        ).all()
        if invites:
            return [await guild.fetch_member(invite.id) for invite in invites]

        return []

    async def add_member(self, member: Member) -> None:
        """Add a member to the database."""
        await self.database_instance.add_member(member)

    async def delete_member(self, member: Member) -> None:
        """Delete a member from the database."""
        await self.database_instance.delete_member(member)

    def _remove_from_lru(self, member_id: int):
        self.get_invited_members.cache_invalidate(member_id)
        self.get_inviter.cache_invalidate(member_id)
