from tortoise import Tortoise
from ..logger import logger


async def init_database(db_url: str):
    """Initialize the database."""

    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["disnake.ext.invitetracker.database.models.__init__"]},
    )
    await Tortoise.generate_schemas()
    logger.info("[+] Database initialized")


async def close_database():
    """Close the database."""
    await Tortoise.close_connections()
