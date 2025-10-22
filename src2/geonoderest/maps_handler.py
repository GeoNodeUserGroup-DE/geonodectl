from .handler_base import HandlerBase
from .capabilities import Listable, Deletable, Patchable, Describable


class MapsHandler(HandlerBase, Listable, Deletable, Patchable, Describable):
    def __init__(self, env):
        super().__init__(env, endpoint="maps", json_object_name="maps")
        # Add any map-specific initialization here

    # You can add map-specific methods here
