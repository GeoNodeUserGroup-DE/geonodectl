from typing import List, Dict, Optional
import logging

from geonoderest.geonodetypes import GeonodeCmdOutObjectKey, GeonodeCmdOutListKey
from geonoderest.exceptions import InvalidPkError
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.rest import GeonodeRest
from geonoderest.jsonsource import JsonSourceError, load_json_source
from geonoderest.cmdprint import (
    print_list_on_cmd,
    print_json,
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

    def cmd_list(self, **kwargs) -> int:
        """show list of geonode obj on the cmdline"""
        obj = self.list(**kwargs)
        if obj is None:
            logging.error("No results returned from GeoNode API.")
            return EXIT_FAILED
        if kwargs["json"]:
            print_json(obj)
        else:
            print_list_on_cmd(obj, self.LIST_CMDOUT_HEADER)
        return EXIT_OK

    def list(self, **kwargs) -> Optional[Dict]:
        """returns dict of datasets from geonode

        Returns:
            Dict: request response
        """
        endpoint = f"{self.ENDPOINT_NAME}/"

        params = self.__handle_http_params__({}, kwargs)
        r = self.http_get(endpoint=endpoint, params=params)
        if r is None:
            return None
        return r[self.JSON_OBJECT_NAME]

    def __parse_pk_string__(self, pk) -> List[int]:
        """
        differentiate between pk range, pk list or single pk

        Args:
            pk (str): pk of the object, as string with range or list or single pk

        Raises:
            InvalidPkError: pk is not a single pk, a range or a list. Raised
                rather than exiting so this stays usable as a library (#69);
                the ``cmd_*`` caller turns it into EXIT_USAGE.
        """

        pk = str(pk)
        # pk range: 5-10
        if "-" in pk:
            try:
                pk_begin, pk_end = pk.split("-")
            except ValueError:
                raise InvalidPkError(f"Invalid pk {pk} found, not a range ...")
            if not all(pk.isdigit() for pk in [pk_begin, pk_end]):
                raise InvalidPkError(f"Invalid pk {pk} found, not an integer ...")
            if int(pk_begin) > int(pk_end):
                # range() would yield nothing, so the command would report
                # success having done nothing at all
                raise InvalidPkError(
                    f"Invalid pk range {pk}, {pk_begin} is greater than {pk_end} ..."
                )
            return [i for i in range(int(pk_begin), int(pk_end) + 1)]

        # pk list: 1,2,3,4,5,6,7
        elif "," in pk:
            pk_list = pk.split(",")
            if not all(x.isdigit() for x in pk_list):
                raise InvalidPkError(f"Invalid pk {pk} found, not an integer ...")
            return [int(i) for i in pk_list]

        # single pk: 1
        else:
            if not pk.isdigit():
                raise InvalidPkError(f"Invalid pk {pk}, is not an integer ...")
            return [int(pk)]

    def cmd_delete(self, pk: str, **kwargs) -> int:
        try:
            pks = self.__parse_pk_string__(pk)
        except InvalidPkError as e:
            logging.error(str(e))
            return EXIT_USAGE

        exit_code = EXIT_OK
        for _pk in pks:
            obj = self.delete(pk=_pk, **kwargs)
            if obj is None:
                logging.error(f"deleting {_pk} failed ... ")
                exit_code = EXIT_FAILED
            else:
                print(f"{self.JSON_OBJECT_NAME}: {_pk} deleted ...")
        return exit_code

    def delete(self, pk: int, **kwargs):
        """delete geonode resource object"""
        return self.http_delete(endpoint=f"{self.ENDPOINT_NAME}/{pk}/")

    def cmd_patch(
        self,
        pk: str,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ) -> int:
        """
        Tries to generate object from incoming json string
        Args:
            pk (str): pk of the object, supports single pk, range (e.g. 5-10) or comma-separated list (e.g. 1,2,3)
            fields (str): string of potential json object
            json_path (str): path to a json file, or a http(s) url serving one

        Returns:
            int: EXIT_OK, EXIT_FAILED if any object could not be patched, or
                EXIT_USAGE for a bad pk or unreadable input json
        """

        if not (json_path or fields):
            logging.error("At least one of 'fields' or 'json_path' must be provided.")
            return EXIT_USAGE
        try:
            json_content = load_json_source(json_path=json_path, fields=fields)
            pks = self.__parse_pk_string__(pk)
        except (JsonSourceError, InvalidPkError) as e:
            logging.error(str(e))
            return EXIT_USAGE

        exit_code = EXIT_OK
        for _pk in pks:
            obj = self.patch(pk=_pk, json_content=json_content, **kwargs)
            if obj is None:
                logging.error(f"patching {_pk} failed ... ")
                exit_code = EXIT_FAILED
            else:
                print_json(obj)
        return exit_code

    def patch(
        self,
        pk: int,
        json_content: Optional[Dict] = None,
        **kwargs,
    ):
        obj = self.http_patch(
            endpoint=f"{self.ENDPOINT_NAME}/{pk}/", json_content=json_content
        )
        return obj

    def cmd_describe(self, pk: str, **kwargs) -> int:
        try:
            pks = self.__parse_pk_string__(pk)
        except InvalidPkError as e:
            logging.error(str(e))
            return EXIT_USAGE

        exit_code = EXIT_OK
        for _pk in pks:
            obj = self.get(pk=_pk, **kwargs)
            if obj is None:
                logging.error(f"describing {_pk} failed ... ")
                exit_code = EXIT_FAILED
            else:
                print_json(obj)
        return exit_code

    def get(self, pk: int, **kwargs) -> Optional[Dict]:
        """get details for a given pk

        Args:
            pk (int): pk of the object

        Returns:
            Dict: obj details
        """
        endpoint = f"{self.ENDPOINT_NAME}/{pk}"
        r = self.http_get(endpoint=endpoint)
        if r is None:
            return None
        return r[self.SINGULAR_RESOURCE_NAME]
