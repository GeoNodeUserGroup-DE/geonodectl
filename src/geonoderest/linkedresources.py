from typing import Dict, List
import logging
import sys

from geonoderest.rest import GeonodeRest
from geonoderest.resources import GeonodeResourceHandler


from .cmdprint import show_list, print_json


class GeonodeLinkedResourcesHandler(GeonodeRest):

    def cmd_add(self, pk: int, linked_to: List[int] = [], **kwargs):
        if len(linked_to) == 0:
            logging.warning(
                "missing linked_to parameter for deletion, doing nothing ... "
            )
            sys.exit(0)
        obj: Dict = self.add(pk=pk, linked_to=linked_to, **kwargs)
        if obj == None:
            logging.warning("add failed ... ")
        else:
            print_json(obj)

    def add(self, pk: int, linked_to: List[int] = [], **kwargs):
        linked_resource_obj: Dict = self.get(pk=pk)
        # target: list = linked_resource_obj["linked_to"] + linked_to
        json_content = {
            "target": list(linked_to),
        }
        endpoint = f"resources/{pk}/linked_resources"
        return self.http_post(endpoint=endpoint, json=json_content)

    def cmd_delete(self, pk: int, linked_to: List[int], **kwargs):
        if len(linked_to) == 0:
            logging.warning(
                "missing linked_to parameter for deletion, doing nothing ... "
            )
            sys.exit(0)

        obj: Dict = self.delete(pk=pk, linked_to=linked_to, **kwargs)
        if obj == None:
            logging.warning("delete failed ... ")
        else:
            print_json(obj)

    def delete(self, pk: int, linked_to: List[int] = [], **kwargs):
        endpoint = f"resources/{pk}/linked_resources"

        json_content = {
            "target": list(linked_to),
        }
        return self.http_delete(endpoint=endpoint, json=json_content)

    def cmd_describe(self, pk: int, **kwargs) -> Dict:
        obj = self.get(pk, **kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:
            linked_to_values = [
                ["linked_to", ref["pk"], ref["resource_type"], ref["title"]]
                for ref in obj["linked_to"]
            ]
            linked_by_values = [
                ["linked_by", ref["pk"], ref["resource_type"], ref["title"]]
                for ref in obj["linked_by"]
            ]
            show_list(
                headers=["link_type", "pk", "resource_type", "title"],
                values=linked_to_values + linked_by_values,
            )

    def get(self, pk, **kwargs) -> Dict:
        endpoint = f"resources/{pk}/linked_resources"

        return self.http_get(endpoint=endpoint)
