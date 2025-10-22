from .handler_base import HandlerBase
from .capabilities import Listable, Describable


class ExecutionRequestHandler(HandlerBase, Listable, Describable):
    def __init__(self, env):
        super().__init__(
            env, endpoint="executionrequest", json_object_name="executionrequest"
        )
        # Add any executionrequest-specific initialization here

    # You can add executionrequest-specific methods here
