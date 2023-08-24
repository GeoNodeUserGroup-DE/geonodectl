from typing import Dict, List

from src.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey
from src.rest import GeonodeRest
from src.cmdprint import print_list_on_cmd, print_json


class GeonodeExecutionRequestHandler(GeonodeRest):
    ENDPOINT_NAME = "executionrequest"
    JSON_OBJECT_NAME = "requests"
    SINGULAR_RESOURCE_NAME = "request"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
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
        print_json(obj)

    def get(self, exec_id: str, **kwargs) -> Dict:
        """
        get details for a given exec_id

        Args:
            exec_id (str): exec_id of the object

        Returns:
            Dict: obj details
        """
        r = self.http_get(
            endpoint=f"{self.ENDPOINT_NAME}/{exec_id}?page_size={kwargs['page_size']}"
        )
        return r[self.SINGULAR_RESOURCE_NAME]

    def cmd_list(self, **kwargs):
        """show list of geonode obj on the cmdline"""
        obj = self.list(**kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:
            print_list_on_cmd(obj, self.LIST_CMDOUT_HEADER)

    def list(self, **kwargs) -> Dict:
        """returns dict of datasets from geonode

        Returns:
            Dict: request response
        """
        r = self.http_get(
            endpoint=f"{self.ENDPOINT_NAME}/?page_size={kwargs['page_size']}"
        )
        return r[self.JSON_OBJECT_NAME]
