from typing import Optional, Dict
import logging

from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.rest import GeonodeRest
from geonoderest.jsonsource import JsonSourceError, load_json_source
from geonoderest.cmdprint import show_list, print_json


class GeonodeAttributeHandler(GeonodeRest):
    """docstring for GeonodeAttributeHandler"""

    # attributes always belong to a dataset
    UUID_RESOURCE_TYPE = "dataset"

    def get(self, pk, **kwargs) -> Dict:
        """
        Get the attributes for a dataset.
        """
        endpoint = f"datasets/{pk}/attribute_set"

        return self.http_get(endpoint=endpoint)

    def cmd_describe(self, pk, **kwargs) -> int:
        """
        Describe the attributes of a dataset.

        :param pk: primary key of the dataset
        :param kwargs: additional keyword arguments
        :return: EXIT_OK, or EXIT_FAILED when the dataset could not be fetched
        """

        pk = self.__resolve_identifier__(pk)
        obj = self.get(pk, **kwargs)
        if obj is None:
            logging.error(f"describing attributes of {pk} failed ... ")
            return EXIT_FAILED
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
        return EXIT_OK

    def cmd_patch(
        self,
        pk,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ) -> int:
        """
        Tries to update object from incoming json string
        Args:
            pk (int): pk of the object
            fields (str): string of potential json object
            json_path (str): path to a json file, or a http(s) url serving one

        Returns:
            int: EXIT_OK, EXIT_FAILED when the patch was rejected, or
                EXIT_USAGE when no readable json was given
        """

        # validated before resolving, so a missing argument is reported as such
        # rather than as a failed uuid lookup - and costs no HTTP call
        if not (json_path or fields):
            logging.error("At least one of 'fields' or 'json_path' must be provided.")
            return EXIT_USAGE
        pk = self.__resolve_identifier__(pk)
        try:
            json_content = load_json_source(json_path=json_path, fields=fields)
        except JsonSourceError as e:
            logging.error(str(e))
            return EXIT_USAGE

        if json_content is None:
            logging.error("No JSON content provided ...")
            return EXIT_USAGE

        obj = self.patch(pk=pk, json_content=json_content, **kwargs)
        if obj is None:
            logging.error(f"patching attributes of {pk} failed ... ")
            return EXIT_FAILED
        print_json(obj)
        return EXIT_OK

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
