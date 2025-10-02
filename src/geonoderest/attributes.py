from typing import Optional, Dict
import logging
import json

from geonoderest.rest import GeonodeRest
from geonoderest.cmdprint import show_list, print_json, json_decode_error_handler


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

    def cmd_patch(
        self,
        pk: int,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ):
        """
        Tries to update object from incoming json string
        Args:
            pk (int): pk of the object
            fields (str): string of potential json object
            json_path (str): path to a json file

        Raises:
            ValueError: catches json.decoder.JSONDecodeError and raises ValueError as decoding is not working
        """

        if json_path:
            with open(json_path, "r") as file:
                try:
                    json_content = json.load(file)
                except json.decoder.JSONDecodeError as E:
                    json_decode_error_handler(str(file), E)

        elif fields:
            try:
                json_content = json.loads(fields)
            except json.decoder.JSONDecodeError as E:
                json_decode_error_handler(fields, E)

        else:
            raise ValueError(
                "At least one of 'fields' or 'json_path' must be provided."
            )

        if json_content is None:
            raise ValueError("No JSON content provided ...")

        obj = self.patch(pk=pk, json_content=json_content, **kwargs)
        print_json(obj)

    def patch(
        self,
        pk: int,
        json_content: Optional[Dict] = None,
        **kwargs,
    ) -> Dict:
        """
        Sends a PATCH request to update attributes of a dataset. Only the 'attribute'/'attributes_set' field is processed.

        Args:
            pk (int): Primary key of the dataset.
            json_content (dict, optional): Data to update.
            **kwargs: Additional arguments for http_patch.

        Returns:
            dict: Server response.

        Raises:
            Exception: If the PATCH request fails.
        """
        endpoint = f"datasets/{pk}/"

        attributes = None
        if json_content is not None and "attribute_set" in json_content:
            attributes = {"attribute": json_content.pop("attribute_set")}

        elif json_content is not None and "attribute" in json_content:
            attributes = {"attribute": json_content.pop("attribute")}

        obj = self.http_patch(endpoint, json_content=attributes, **kwargs)
        return obj
