from typing import Dict, List
import logging

from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.identifier import ANY_RESOURCE_TYPE
from geonoderest.rest import GeonodeRest
from geonoderest.resources import GeonodeResourceHandler


from .cmdprint import show_list, print_json


class GeonodeLinkedResourcesHandler(GeonodeRest):
    # any resource type can be linked to any other
    UUID_RESOURCE_TYPE = ANY_RESOURCE_TYPE

    def cmd_add(self, pk, linked_to=None, **kwargs) -> int:
        # argparse leaves --linked-to unset as None, not as an empty list.
        # checked before resolving so an unset variable costs no HTTP call
        if not linked_to:
            # an unset shell variable must not pass as a successful no-op (#151)
            logging.error("no --linked-to pks given, nothing to add ... ")
            return EXIT_USAGE
        pk = self.__resolve_identifier__(pk)
        linked_to = self.__resolve_identifiers__(linked_to)
        obj: Dict = self.add(pk=pk, linked_to=linked_to, **kwargs)
        if obj is None:
            logging.error("add failed ... ")
            return EXIT_FAILED
        print_json(obj)
        return EXIT_OK

    def add(self, pk: int, linked_to: List[int] = [], **kwargs):
        linked_resource_obj: Dict = self.get(pk=pk)
        # target: list = linked_resource_obj["linked_to"] + linked_to
        json_content = {
            "target": list(linked_to),
        }
        endpoint = f"resources/{pk}/linked_resources"
        return self.http_post(endpoint=endpoint, json=json_content)

    def cmd_delete(self, pk, linked_to=None, **kwargs) -> int:
        # argparse leaves --linked-to unset as None, not as an empty list.
        # checked before resolving so an unset variable costs no HTTP call
        if not linked_to:
            # an unset shell variable must not pass as a successful no-op (#151)
            logging.error("no --linked-to pks given, nothing to delete ... ")
            return EXIT_USAGE

        pk = self.__resolve_identifier__(pk)
        linked_to = self.__resolve_identifiers__(linked_to)
        obj: Dict = self.delete(pk=pk, linked_to=linked_to, **kwargs)
        if obj is None:
            logging.error("delete failed ... ")
            return EXIT_FAILED
        print_json(obj)
        return EXIT_OK

    def delete(self, pk: int, linked_to: List[int] = [], **kwargs):
        endpoint = f"resources/{pk}/linked_resources"

        json_content = {
            "target": list(linked_to),
        }
        return self.http_delete(endpoint=endpoint, json=json_content)

    def cmd_describe(self, pk, **kwargs) -> int:
        pk = self.__resolve_identifier__(pk)
        obj = self.get(pk, **kwargs)
        if obj is None:
            logging.error(f"describing linked resources of {pk} failed ... ")
            return EXIT_FAILED
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
        return EXIT_OK

    def get(self, pk, **kwargs) -> Dict:
        endpoint = f"resources/{pk}/linked_resources"

        return self.http_get(endpoint=endpoint)
