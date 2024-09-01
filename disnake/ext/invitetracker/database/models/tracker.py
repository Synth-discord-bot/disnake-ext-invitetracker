import tortoise


class GuildInviteModel(tortoise.Model):
    code = tortoise.fields.CharField(max_length=255)
    uses = tortoise.fields.IntField(default=0)

    class Meta:
        table = "guild_invite"


class GuildModel(tortoise.Model):
    id = tortoise.fields.BigIntField(pk=True)  # TODO: rename to guild_id
    invites = tortoise.fields.ManyToManyField(
        "models.GuildInviteModel", related_name="guilds"
    )

    class Meta:
        table = "guild"


class UserInvitedModel(tortoise.Model):
    id = tortoise.fields.BigIntField(pk=True)
    guild_id = tortoise.fields.BigIntField()
    invite_code = tortoise.fields.CharField(max_length=255)
    joined_at = tortoise.fields.DatetimeField()
    inviter_id = tortoise.fields.BigIntField(null=True)

    class Meta:
        table = "user_invited"


class UserInviteModel(tortoise.Model):
    code = tortoise.fields.CharField(max_length=255)
    invited = tortoise.fields.ForeignKeyField(
        "models.UserInvitedModel", related_name="invited"
    )

    class Meta:
        table = "user_invite"


class UserModel(tortoise.Model):
    id = tortoise.fields.BigIntField(pk=True)
    invited = tortoise.fields.ManyToManyField(
        "models.UserInviteModel", related_name="users"
    )

    class Meta:
        table = "user"
