import os
from pathlib import Path
from typing import List, Dict
import logging

from geonoderest.rest import GeonodeRest
from geonoderest.cmdprint import print_list_on_cmd, show_list, print_json
from geonoderest.geonodetypes import GeonodeCmdOutListKey


class GeonodeAttributeHandler(GeonodeRest):
    """docstring for GeonodeAttributeHandler"""
    

    def get(self, pk, **kwargs) -> Dict:
        """
        Get the attributes for a dataset.
        """
        endpoint = f"datasets/{pk}/attribute_set"

        return self.http_get(endpoint=endpoint)

    def cmd_describe(self, pk: int, **kwargs) -> Dict:
        """
        Describe the attributes of a dataset.

        :param pk: primary key of the dataset
        :param kwargs: additional keyword arguments
        :return: dictionary containing the attributes of the dataset
        """

        obj = self.get(pk, **kwargs)
        if kwargs["json"]:
            print_json(obj)
        else:

            attributes = [
                [
                    attr["pk"],
                    attr["attribute"],
                    attr["attribute_label"],
                    attr["description"],
                    attr["attribute_type"],
                ]
                for attr in obj["attributes"]
            ]
            show_list(
                headers=[
                    "pk",
                    "attribute",
                    "attribute_label",
                    "description",
                    "attribute_type",
                ],
                values=attributes,
            )
        return {}
