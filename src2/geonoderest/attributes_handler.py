from .handler_base import HandlerBase
from .capabilities import AttributeDescribeCapable, AttributePatchCapable


class AttributesHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(env, endpoint="attributes", json_object_name="attributes")
        self.attr_describe = AttributeDescribeCapable(self)
        self.attr_patch = AttributePatchCapable(self)

    def get(self, *args, **kwargs):
        return self.attr_describe.get(*args, **kwargs)

    def cmd_describe(self, *args, **kwargs):
        return self.attr_describe.cmd_describe(*args, **kwargs)

    def cmd_patch(self, *args, **kwargs):
        return self.attr_patch.cmd_patch(*args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.attr_patch.patch(*args, **kwargs)
