from typing import Dict, TypeVar

from disnake import Invite
from .logger.logger import logger

T = TypeVar("T", bound=Dict[int, Dict[str, Invite]])

version = "1.2.1"
__all__ = ("InviteTracker",)
