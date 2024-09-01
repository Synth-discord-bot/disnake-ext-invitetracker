from typing import Dict, TypeVar

from disnake import Invite

T = TypeVar("T", bound=Dict[int, Dict[str, Invite]])

version = "1.3.1.1"
__all__ = ("InviteTracker",)
