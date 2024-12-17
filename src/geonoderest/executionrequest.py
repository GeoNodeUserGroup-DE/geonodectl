from typing import Dict, List
import logging

from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey
from geonoderest.rest import GeonodeRest

from geonoderest.cmdprint import print_list_on_cmd, print_json


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
        r = self.http_get(endpoint=f"{self.ENDPOINT_NAME}/{exec_id}")
        return r[self.SINGULAR_RESOURCE_NAME]

    def cmd_list(self, **kwargs):
        """show list of geonode obj on the cmdline"""
        obj = self.list(**kwargs)
        if obj is None:
            logging.warning("getting list failed ...")
            return None
        if kwargs["json"]:
            print_json(obj)
        else:
            print_list_on_cmd(obj, self.LIST_CMDOUT_HEADER)

    def list(self, **kwargs) -> Dict:
        """returns dict of execution requests from geonode

        Returns:
            Dict: request response
        """
        endpoint = f"{self.ENDPOINT_NAME}/"

        params = self.__handle_http_params__({}, kwargs)
        r = self.http_get(endpoint=endpoint, params=params)
        if r is None:
            return None
        return r[self.JSON_OBJECT_NAME]
