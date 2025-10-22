from .handler_base import HandlerBase
from .capabilities import Listable, Deletable


class UploadsHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(env, endpoint="uploads", json_object_name="uploads")
        self.listable = Listable(self)
        self.deletable = Deletable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def delete(self, pk, **kwargs):
        return self.deletable.delete(pk, **kwargs)
