from typing import List, Dict, Optional
import json

from geonoderest.geonodetypes import GeonodeCmdOutObjectKey, GeonodeCmdOutListKey
from geonoderest.rest import GeonodeRest
from geonoderest.cmdprint import (
    print_list_on_cmd,
    print_json,
    json_decode_error_handler,
)


class GeonodeObjectHandler(GeonodeRest):
    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(type=list, key="pk")
    ]
    GET_CMDOUT_PROPERTIES: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(type=list, key="pk")
    ]
    DEFAULT_UPLOAD_KEYS: List[str] = ["key", "value"]
    JSON_OBJECT_NAME: str = ""
    ENDPOINT_NAME: str = ""
    SINGULAR_RESOURCE_NAME: str = ""

    def __handle_http_params__(self, params: Dict, kwargs: Dict) -> Dict:
        if "page_size" in kwargs:
            params["page_size"] = kwargs["page_size"]
        if "page" in kwargs:
            params["page"] = kwargs["page"]

        if "filter" in kwargs and kwargs["filter"] is not None:
            for field, value in kwargs["filter"].items():
                field = "filter{" + field + "}"
                params[field] = value

        return params

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
        endpoint = f"{self.ENDPOINT_NAME}/"

        params = self.__handle_http_params__({}, kwargs)

        r = self.http_get(endpoint=endpoint, params=params)
        return r[self.JSON_OBJECT_NAME]

    def cmd_delete(self, pk: int, **kwargs):
        self.delete(pk=pk, **kwargs)
        print(f"{self.JSON_OBJECT_NAME}: {pk} deleted ...")

    def delete(self, pk: int, **kwargs):
        """delete geonode resource object"""
        self.http_get(endpoint=f"{self.ENDPOINT_NAME}/{pk}")
        self.http_delete(endpoint=f"resources/{pk}/delete")

    def cmd_patch(
        self,
        pk: int,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ):
        """
        Tries to generate object from incoming json string
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

                if json_content is not None and "attribute_set" in json_content:
                    json_content.pop("attribute_set", None)

        elif fields:
            try:
                json_content = json.loads(fields)
            except json.decoder.JSONDecodeError as E:
                json_decode_error_handler(fields, E)

        else:
            raise ValueError(
                "At least one of 'fields' or 'json_path' must be provided."
            )

        obj = self.patch(pk=pk, json_content=json_content, **kwargs)
        print_json(obj)

    def patch(
        self,
        pk: int,
        json_content: Optional[Dict] = None,
        **kwargs,
    ):
        obj = self.http_patch(endpoint=f"{self.ENDPOINT_NAME}/{pk}/", data=json_content)
        return obj

    def cmd_describe(self, pk: int, **kwargs):
        obj = self.get(pk=pk, **kwargs)
        print_json(obj)

    def get(self, pk: int, **kwargs) -> Dict:
        """get details for a given pk

        Args:
            pk (int): pk of the object

        Returns:
            Dict: obj details
        """
        endpoint = f"{self.ENDPOINT_NAME}/{pk}"
        r = self.http_get(endpoint=endpoint)
        return r[self.SINGULAR_RESOURCE_NAME]
