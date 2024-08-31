from tortoise import Model, fields


class InviteModel(Model):
    code = fields.CharField(max_length=255)
    uses = fields.IntField(default=0)

    class Meta:
        table = "invite"


class GuildModel(Model):
    id = fields.BigIntField(pk=True)
    invites = fields.ManyToManyField("models.InviteModel", related_name="guilds")

    class Meta:
        table = "guild"
