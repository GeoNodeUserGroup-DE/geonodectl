from typing import Dict, List

from .geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey, LinkedResourcesRelation
from .rest import GeonodeRest

from .cmdprint import print_list_on_cmd, print_json
    ENDPOINT = "resources"


class LinkedResourcesHandler(GeonodeRest):

    def cmd_set(self, from_pks: list = [], to_pks: list = [], **kwargs):
        pass

    def set(self, from_pks: list = [], to_pks: list = [], **kwargs):
        pass

    def cmd_add(self, relation: LinkedResourcesRelation, pk: int, **kwargs):
        pass

    def add(self, relation: LinkedResourcesRelation, pk: int, **kwargs):
        pass

    def cmd_delete(self, relation: LinkedResourcesRelation, pk: int, **kwargs):
        pass

    def delete(self, relation: LinkedResourcesRelation, pk: int, **kwargs):
        pass

    def cmd_list(self, pk, **kwargs) -> Dict:
        obj = self.list(**kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:
            # TODO
            print(obj)

    def list(self, pk, **kwargs) -> Dict:
        endpoint = f"resources/{pk}/linked_resources"

        params = self.__handle_http_params__({}, kwargs)
        r = self.http_get(endpoint=endpoint, params=params)
        return r[self.JSON_OBJECT_NAME]
