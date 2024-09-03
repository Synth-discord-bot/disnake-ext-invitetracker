from typing import Dict, TypeVar

from disnake import Invite

T = TypeVar("T", bound=Dict[int, Dict[str, Invite]])

version = "1.5.0"
__all__ = ("InviteTracker",)
