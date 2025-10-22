from .handler_base import HandlerBase
from .capabilities import Listable, Describable


class TKeywordsHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(env, endpoint="tkeywords", json_object_name="tkeywords")
        self.listable = Listable(self)
        self.describable = Describable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def describe(self, pk, **kwargs):
        return self.describable.describe(pk, **kwargs)
