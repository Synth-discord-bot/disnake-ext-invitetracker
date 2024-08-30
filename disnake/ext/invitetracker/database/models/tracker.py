from tortoise import fields
from .invite import InviteModel


class Tracker(InviteModel):
    uses = fields.BigIntField(default=0)

    class Meta:
        table = "tracker"

    def __str__(self) -> str:
        return f"uses={self.uses}"
