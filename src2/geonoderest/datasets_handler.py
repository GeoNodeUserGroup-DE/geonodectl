from .handler_base import HandlerBase
from .capabilities import Listable, Deletable, Patchable, Describable, UploadCapable


class DatasetsHandler(HandlerBase):
    def __init__(self, env):
        super().__init__(env, endpoint="datasets", json_object_name="datasets")
        self.listable = Listable(self)
        self.deletable = Deletable(self)
        self.patchable = Patchable(self)
        self.describable = Describable(self)
        self.upload_capable = UploadCapable(self)

    def list(self, **kwargs):
        return self.listable.list(**kwargs)

    def delete(self, pk, **kwargs):
        return self.deletable.delete(pk, **kwargs)

    def patch(self, pk, fields, **kwargs):
        return self.patchable.patch(pk, fields, **kwargs)

    def describe(self, pk, **kwargs):
        return self.describable.describe(pk, **kwargs)

    def cmd_upload(self, *args, **kwargs):
        return self.upload_capable.cmd_upload(*args, **kwargs)

    def upload(self, *args, **kwargs):
        return self.upload_capable.upload(*args, **kwargs)
