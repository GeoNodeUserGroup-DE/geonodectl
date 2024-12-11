from typing import Dict, List
import logging
import sys

from geonoderest.rest import GeonodeRest
from geonoderest.resources import GeonodeResourceHandler


from .cmdprint import show_list, print_json


class GeonodeLinkedResourcesHandler(GeonodeRest):

    @staticmethod
    def __print_linked_resources_of_object__(obj: dict) -> None:
        linked_to_values = [ [ "linked_to", ref["pk"], ref["resource_type"], ref["title"] ] for ref in obj["linked_to"] ]
        linked_by_values = [ [ "linked_by", ref["pk"], ref["resource_type"], ref["title"] ] for ref in obj["linked_by"] ]
        show_list(headers=["link_type", "pk", "resource_type","title"], values=linked_to_values + linked_by_values)

    def cmd_patch(self, pk: int, linked_to: List[int] = [], linked_by: List[int] = [], **kwargs):
        gn_resources_handler = GeonodeResourceHandler(self.gn_credentials)
        a = gn_resources_handler.get(pk)

        if not all( gn_resources_handler.get(pk) for pk in linked_to ):
            raise ValueError("not all resources in patch (linked_to) available in geonode ...")
        if not all( gn_resources_handler.get(pk) for pk in linked_by ):
            raise ValueError("not all resources in patch (linked_by) available in geonode ...")
        
        json_content = {
            "linked_to": linked_to,
            "linked_by": linked_by
        }

        obj: Dict = self.patch(pk=pk, json_content=json_content, **kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:
            GeonodeLinkedResourcesHandler.__print_linked_resources_of_object__(obj)

    def patch(self, pk: int, json_content:Dict, **kwargs):
        endpoint = f"resources/{pk}/linked_resources"
        breakpoint()
        obj = self.http_patch(endpoint=endpoint, params=json_content)
        return obj

    def cmd_add(self, pk: int, linked_to: List[int] = [], linked_by: List[int] = [], **kwargs):
        if len(linked_by) == 0 and len(linked_to) == 0:
            logging.warning("missing linked-by or linked-to parameter for deletion, doing nothing ... ")
            sys.exit(0)
        obj: Dict = self.add(pk=pk,linked_to=linked_to, linked_by=linked_by, **kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:
            GeonodeLinkedResourcesHandler.__print_linked_resources_of_object__(obj)
    

    def add(self, pk: int, linked_to: List[int] = [], linked_by: List[int] = [], **kwargs):
        
        linked_resource_obj: Dict = self.get(pk=pk)

        linked_resource_obj["linked_to"] = linked_resource_obj["linked_to"].extend(linked_to)
        linked_resource_obj["linked_by"] = linked_resource_obj["linked_by"].extend(linked_by)
        
        json_content = {
            "linked_to": list(linked_to),
            "linked_by": list(linked_by)
        }

        self.patch(pk=pk, json_content=json_content, **kwargs)


    def cmd_delete(self, pk: int, linked_by: List[int], linked_to: List[int], **kwargs):
        if len(linked_by) == 0 and len(linked_to) == 0:
            logging.warning("missing linked-by or linked-to parameter for deletion, doing nothing ... ")
            sys.exit(0)

        obj: Dict = self.delete(pk=pk,linked_to=linked_to, linked_by=linked_by, **kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:
            GeonodeLinkedResourcesHandler.__print_linked_resources_of_object__(obj)


    def delete(self, pk: int, linked_to: List[int] = [], linked_by: List[int] = [], **kwargs):

        linked_resource_obj: Dict = self.get(pk=pk)

        # check if all pk's to delete are available else refuse ...
        check_linked_to = all( obj["pk"] in linked_to for obj in linked_resource_obj["linked_to"])
        check_linked_by = all( obj["pk"] in linked_by for obj in linked_resource_obj["linked_by"])
        if not check_linked_by or not check_linked_to:
            raise ValueError("all pk's in linked_to and linked_by parameters must be part of the given pk to perform delete operation ...")

        def not_to_delete(e,linked_to):
            return True if e not in linked_to else False

        json_content = {
            "linked_to": filter(not_to_delete(linked_to), linked_resource_obj["linked_to"]),
            "linked_by": filter(not_to_delete(linked_by), linked_resource_obj["linked_by"])
        }

        self.patch(pk=pk, json_content=json_content, **kwargs)

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