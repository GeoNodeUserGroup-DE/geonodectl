from .handler_base import HandlerBase
from .capabilities import Listable, Deletable, LinkedResourceCapable


class LinkedResourcesHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(
            env, endpoint="linked-resources", json_object_name="linked_resources"
        )
        self.listable = Listable(self)
        self.deletable = Deletable(self)
        self.linked_resource = LinkedResourceCapable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def delete(self, pk, **kwargs):
        return self.deletable.delete(pk, **kwargs)

    def cmd_add(self, *args, **kwargs):
        return self.linked_resource.cmd_add(*args, **kwargs)

    def add(self, *args, **kwargs):
        return self.linked_resource.add(*args, **kwargs)

    def cmd_delete(self, *args, **kwargs):
        return self.linked_resource.cmd_delete(*args, **kwargs)

    def delete_linked(self, *args, **kwargs):
        return self.linked_resource.delete(*args, **kwargs)

    def cmd_describe(self, *args, **kwargs):
        return self.linked_resource.cmd_describe(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.linked_resource.get(*args, **kwargs)
