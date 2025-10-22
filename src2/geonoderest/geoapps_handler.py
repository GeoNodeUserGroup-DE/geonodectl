from .handler_base import HandlerBase
from .capabilities import Listable, Deletable, Patchable, Describable


class GeoappsHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(env, endpoint="geoapps", json_object_name="geoapps")
        self.listable = Listable(self)
        self.deletable = Deletable(self)
        self.patchable = Patchable(self)
        self.describable = Describable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def delete(self, pk, **kwargs):
        return self.deletable.delete(pk, **kwargs)

    def patch(self, pk, fields, **kwargs):
        return self.patchable.patch(pk, fields, **kwargs)

    def describe(self, pk, **kwargs):
        return self.describable.describe(pk, **kwargs)
