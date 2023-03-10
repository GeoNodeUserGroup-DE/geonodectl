from typing import List, Dict
import pprint

from src.geonodetypes import GeonodeCmdOutObjectKey, GeonodeCmdOutListKey
from src.rest import GeonodeRest
from src.cmdprint import show_list


class GeonodeObjectHandler(GeonodeRest):
    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(type=list, key="pk")
    ]
    GET_CMDOUT_PROPERTIES: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(type=list, key="pk")
    ]
    DEFAULT_UPLOAD_KEYS: List[str] = ["key", "value"]
    RESOURCE_TYPE: str = ""
    SINGULAR_RESOURCE_NAME: str = ""

    def cmd_list(self, **kwargs):
        """show list of geonode obj on the cmdline"""
        obj = self.list(**kwargs)
        if kwargs["json"]:
            pprint.pprint(obj)
        else:
            self.__class__.print_list_on_cmd(obj)

    def list(self, **kwargs) -> Dict:
        """returns dict of datasets from geonode

        Returns:
            Dict: request response
        """
        r = self.http_get(
            endpoint=f"{self.RESOURCE_TYPE}/?page_size={kwargs['page_size']}"
        )
        return r[self.RESOURCE_TYPE]

    def cmd_delete(self, pk: int, **kwargs):
        self.delete(pk=pk, **kwargs)
        print(f"{self.RESOURCE_TYPE}: {pk} deleted ...")

    def delete(self, pk: int, **kwargs):
        """delete geonode resource object"""
        pk = kwargs["pk"]
        self.http_get(endpoint=f"{self.RESOURCE_TYPE}/{pk}")
        self.http_delete(endpoint=f"resources/{pk}/delete")

    def cmd_patch(self, pk: int, fields: Dict, **kwargs):
        obj = self.patch(pk, fields, **kwargs)
        pprint.pprint(obj)

    def patch(self, pk: int, fields: Dict, **kwargs) -> Dict:
        print(f"setting up value(s): {fields}")
        return self.http_patch(endpoint=f"{self.RESOURCE_TYPE}/{pk}/", params=fields)

    def cmd_describe(self, pk: int, **kwargs):
        obj = self.get(pk=pk, **kwargs)
        pprint.pprint(obj)

    def get(self, pk: int, **kwargs) -> Dict:
        """get details for a given pk

        Args:
            pk (int): pk of the object

        Returns:
            Dict: obj details
        """
        r = self.http_get(
            endpoint=f"{self.RESOURCE_TYPE}/{pk}?page_size={kwargs['page_size']}"
        )
        return r[self.SINGULAR_RESOURCE_NAME]

    @classmethod
    def cmd_list_header(self) -> List[str]:
        """returns the default header to print list on cmd

        Returns:
            List[str]: list of header elements as str
        """
        return [str(cmdoutkey) for cmdoutkey in self.LIST_CMDOUT_HEADER]

    @classmethod
    def print_list_on_cmd(cls, obj: Dict):
        """print a beautiful list on the cmdline

        Args:
            obj (Dict): dict object to print on cmd line
        """

        def generate_line(i, obj: Dict, headers: List[GeonodeCmdOutObjectKey]) -> List:
            return [cmdoutkey.get_key(obj[i]) for cmdoutkey in headers]

        values = [
            generate_line(i, obj, cls.LIST_CMDOUT_HEADER) for i in range(len(obj))
        ]
        show_list(headers=cls.cmd_list_header(), values=values)
