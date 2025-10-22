from .handler_base import HandlerBase
from .capabilities import Listable, Describable, KeywordLabelGetCapable


class TKeywordLabelsHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(
            env, endpoint="tkeywordlabels", json_object_name="tkeywordlabels"
        )
        self.listable = Listable(self)
        self.describable = Describable(self)
        self.keyword_label_get = KeywordLabelGetCapable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def describe(self, pk, **kwargs):
        return self.describable.describe(pk, **kwargs)

    def get(self, pk, **kwargs):
        return self.keyword_label_get.get(pk, **kwargs)
