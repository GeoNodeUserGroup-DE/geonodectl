from typing import Dict, List

from .geonodetypes import GeonodeCmdOutListKey,GeonodeCmdOutDictKey, GeonodeCmdOutObjectKey, LinkedResourcesRelation
from .rest import GeonodeRest

from .cmdprint import show_list, print_json, print_list_on_cmd



class GeonodeLinkedResourcesHandler(GeonodeRest):

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key=["pk"])
    ]

    @classmethod
    def __print_linked_resources_of_object__(obj: dict) -> None:
        linked_to_values = [ [ "linked_to", ref["pk"], ref["resource_type"], ref["title"] ] for ref in obj["linked_to"] ]
        linked_by_values = [ [ "linked_by", ref["pk"], ref["resource_type"], ref["title"] ] for ref in obj["linked_by"] ]
        show_list(headers=["link_type", "pk", "resource_type","title"], values=linked_to_values + linked_by_values)

    def cmd_set(self, from_pks: list = [], to_pks: list = [], **kwargs):
        pass

    def set(self, from_pks: list = [], to_pks: list = [], **kwargs):
        pass

    def cmd_add(self, relation: LinkedResourcesRelation, pk: int, **kwargs):
        pass

    def add(self, relation: LinkedResourcesRelation, pk: int, **kwargs):
        pass

    def cmd_delete(self, pk: int, linked_by: List[int], linked_to: List[int], **kwargs):
        pass

    def delete(self, relation: LinkedResourcesRelation, pk: int, **kwargs):
        pass

    def cmd_describe(self, pk: int, **kwargs) -> Dict:
        obj = self.get(pk,**kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:
            GeonodeLinkedResourcesHandler.__print_linked_resources_of_object__(obj)

    def get(self, pk, **kwargs) -> Dict:
        endpoint = f"resources/{pk}/linked_resources"

        r = self.http_get(endpoint=endpoint)
        return r