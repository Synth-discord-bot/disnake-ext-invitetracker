from tortoise import Model, fields


class GuildInviteModel(Model):
    code = fields.CharField(max_length=255)
    uses = fields.IntField(default=0)

    class Meta:
        table = "guild_invite"


class GuildModel(Model):
    id = fields.BigIntField(pk=True)
    invites = fields.ManyToManyField("models.GuildInviteModel", related_name="guilds")

    class Meta:
        table = "guild"


class UserInvitedModel(Model):
    id = fields.BigIntField(pk=True)
    code = fields.CharField(max_length=255)
    joined_at = fields.DatetimeField()

    class Meta:
        table = "user_invited"


class UserInviteModel(Model):
    code = fields.CharField(max_length=255)
    invited = fields.ForeignKeyField("models.UserInvitedModel", related_name="invited")

    class Meta:
        table = "user_invite"


class UserModel(Model):
    id = fields.BigIntField(pk=True)
    invited = fields.ManyToManyField("models.UserInviteModel", related_name="users")

    class Meta:
        table = "user"
