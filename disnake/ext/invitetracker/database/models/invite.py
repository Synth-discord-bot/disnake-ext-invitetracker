from tortoise import Model, fields


class InviteModel(Model):
    code = fields.CharField(pk=True, max_length=60)
    guild_id = fields.BigIntField()

    class Meta:
        abstract = True
