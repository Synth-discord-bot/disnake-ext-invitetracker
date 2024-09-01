from typing import Dict, TypeVar
import sys
from loguru import logger

from disnake import Invite

T = TypeVar("T", bound=Dict[int, Dict[str, Invite]])

version = "1.3.1.1"
__all__ = ("InviteTracker",)


def logging_setup():
    """
    Set up the logging format for the bot.

    This function sets up the logging to have a format of
    `<blue>{time:HH:mm:ss.SS}</blue> | <green>{message}</green>` for INFO level
    messages and `<blue>{time:HH:mm:ss.SS}</blue> | <red>{message}</red>` for ERROR
    level messages.

    The logging level is set to INFO and the filter is set to only show messages
    that are not ERROR level.

    The logging is added to sys.stdout, which is the standard output stream.
    """

    format_info = "<blue>{time:HH:mm:ss.SS}</blue> | <green>{message}</green>"
    format_error = "<blue>{time:HH:mm:ss.SS}</blue> | <red>{message}</red>"

    logger.remove()

    logger.add(
        sys.stdout,
        colorize=True,
        format=format_info,
        level="INFO",
        filter=lambda record: record["level"].name != "ERROR",
    )
    logger.add(sys.stdout, colorize=True, format=format_error, level="ERROR")


logging_setup()
