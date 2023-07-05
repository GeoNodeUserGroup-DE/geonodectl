from typing import Dict

from src.resources import GeonodeResourceHandler
from src.geonodetypes import GeonodeCmdOutListKey


class GeonodeExecutionRequestHandler(GeonodeResourceHandler):
    ENDPOINT_NAME = "executionrequest"
    JSON_OBJECT_NAME = "requests"
    SINGULAR_RESOURCE_NAME = "request"

    # TODO
    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="exec_id"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="status"),
        GeonodeCmdOutListKey(key="user"),
        GeonodeCmdOutListKey(key="source"),
        GeonodeCmdOutListKey(key="created"),
        GeonodeCmdOutListKey(key="log"),
    ]

    def cmd_describe(self, exec_id: str, **kwargs):
        obj = self.get(exec_id=exec_id, **kwargs)
        self.print_json(obj)

    def get(self, exec_id: str, **kwargs) -> Dict:
        """get details for a given exec_id

        Args:
            exec_id (int): exec_id of the object

        Returns:
            Dict: obj details
        """
        r = self.http_get(
            endpoint=f"{self.ENDPOINT_NAME}/{exec_id}?page_size={kwargs['page_size']}"
        )
        return r[self.SINGULAR_RESOURCE_NAME]
