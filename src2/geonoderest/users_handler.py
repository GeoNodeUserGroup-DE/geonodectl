from .handler_base import HandlerBase
from .capabilities import (
    Listable,
    Deletable,
    Patchable,
    Describable,
    UserDescribeCapable,
    UserPatchCapable,
    UserCreateCapable,
)


class UsersHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(env, endpoint="users", json_object_name="users")
        self.listable = Listable(self)
        self.deletable = Deletable(self)
        self.patchable = Patchable(self)
        self.describable = Describable(self)
        self.user_describe = UserDescribeCapable(self)
        self.user_patch = UserPatchCapable(self)
        self.user_create = UserCreateCapable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def delete(self, pk, **kwargs):
        return self.deletable.delete(pk, **kwargs)

    def patch(self, pk, fields, **kwargs):
        return self.patchable.patch(pk, fields, **kwargs)

    def describe(self, pk, **kwargs):
        return self.describable.describe(pk, **kwargs)

    def cmd_describe(self, *args, **kwargs):
        return self.user_describe.cmd_describe(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.user_describe.get(*args, **kwargs)

    def cmd_patch(self, *args, **kwargs):
        return self.user_patch.cmd_patch(*args, **kwargs)

    def user_patch_method(self, *args, **kwargs):
        return self.user_patch.patch(*args, **kwargs)

    def cmd_create(self, *args, **kwargs):
        return self.user_create.cmd_create(*args, **kwargs)

    def create(self, *args, **kwargs):
        return self.user_create.create(*args, **kwargs)
