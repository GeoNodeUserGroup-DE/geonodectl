from .handler_base import HandlerBase
from .capabilities import Listable, Deletable, Patchable, Describable, MetadataCapable


class ResourceHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(env, endpoint="resources", json_object_name="resources")
        self.listable = Listable(self)
        self.deletable = Deletable(self)
        self.patchable = Patchable(self)
        self.describable = Describable(self)
        self.metadata_capable = MetadataCapable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def delete(self, pk, **kwargs):
        return self.deletable.delete(pk, **kwargs)

    def patch(self, pk, fields, **kwargs):
        return self.patchable.patch(pk, fields, **kwargs)

    def describe(self, pk, **kwargs):
        return self.describable.describe(pk, **kwargs)

    def cmd_metadata(self, *args, **kwargs):
        return self.metadata_capable.cmd_metadata(*args, **kwargs)

    def metadata(self, *args, **kwargs):
        return self.metadata_capable.metadata(*args, **kwargs)
