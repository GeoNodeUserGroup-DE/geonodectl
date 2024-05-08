import json
from typing import Dict, Optional

from geonoderest.resources import GeonodeResourceHandler
from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey
from geonoderest.cmdprint import (
    print_list_on_cmd,
    print_json,
    json_decode_error_handler,
)


class GeonodeUsersHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "users"
    SINGULAR_RESOURCE_NAME = "user"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="username"),
        GeonodeCmdOutListKey(key="first_name"),
        GeonodeCmdOutListKey(key="last_name"),
        GeonodeCmdOutListKey(key="email"),
        GeonodeCmdOutListKey(key="is_staff"),
        GeonodeCmdOutListKey(key="is_superuser"),
    ]

    def cmd_describe(
        self, pk: int, user_resources: bool = False, user_groups: bool = False, **kwargs
    ):
        """show requested user in detail on cmd. Further show groups or accessable items of user

        Args:
            pk (int): id of user to show in detail
            user_resources (bool, optional): if set to true ressources accessable
                                             by given user are listed. Defaults to False.
            user_groups (bool, optional): if set to true groups of given user are printed.
                                          Defaults to False.

        Raises:
            SystemExit: if user_resource and user_groups are true at the same time this function gets confused and exits
        """

        obj = self.get(
            pk, user_resources=user_resources, user_groups=user_groups, **kwargs
        )
        # in this case print as list of ressources
        if user_resources is True:
            print_list_on_cmd(
                obj["resources"], GeonodeResourceHandler.LIST_CMDOUT_HEADER
            )
        else:
            print_json(obj)

    def get(
        self, pk: int, user_resources: bool = False, user_groups: bool = False, **kwargs
    ) -> Dict:
        """get user details

        Args:
            pk (int): id of user to get details about
            user_resources (bool, optional): if set to true ressources accessable by given user are returned.
                                            Defaults to False.
            user_groups (bool, optional): if set to true groups of given user are returned.
                                            Defaults to False.

        Raises:
            AttributeError: if user_resource and user_groups are true at the same time this function gets confused and exits

        Returns:
            Dict: requested info, details of user or list of accessable resources or groups of user are returned
        """
        if user_resources and user_groups:
            raise AttributeError(
                "cannot handle user_resources and user_groups True at the same time ..."
            )
        r: Dict
        if user_groups is True:
            r = self.http_get(
                endpoint=f"{self.ENDPOINT_NAME}/{pk}/groups?page_size={kwargs['page_size']}&page={kwargs['page']}"
            )
            return r
        elif user_resources is True:
            endpoint = f"{GeonodeResourceHandler.ENDPOINT_NAME}?page_size={kwargs['page_size']}&page={kwargs['page']}"
            endpoint += "&filter{owner.pk}=" + str(pk)
            r = self.http_get(endpoint=endpoint)
            return r
        else:
            r = self.http_get(
                endpoint=f"{self.ENDPOINT_NAME}/{pk}?page_size={kwargs['page_size']}&page={kwargs['page']}"
            )
            return r[self.SINGULAR_RESOURCE_NAME]

    def cmd_patch(
        self,
        pk: int,
        fields: Optional[str] = None,  # JSON string or path to JSON file
        json_path: Optional[str] = None,  # Path to JSON file
        **kwargs,
    ):
        """Patch user details and print the result.

        Args:
            pk (int): User ID.
            fields (Optional[str]): JSON string. Defaults to None.
            json_path (Optional[str]): Path to JSON file. Defaults to None.
            kwargs: Additional keyword arguments.
        """
        # Load JSON content from file or string
        json_content = None
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

        if json_content is None:
            raise ValueError(
                "At least one of 'fields' or 'json_path' must be provided."
            )

        # Apply patch and print result
        obj = self.patch(pk=pk, json_content=json_content, **kwargs)
        print_json(obj)

    def patch(
        self,
        pk: int,
        json_content: Optional[Dict] = None,
        **kwargs,
    ) -> Dict:
        """Patch user details and return the result.

        Args:
            pk (int): User ID.
            json_content (Optional[Dict]): JSON content to patch.
            kwargs: Additional keyword arguments.

        Returns:
            Dict: Updated user details.
        """

        # Send a PATCH request to the GeoNode API to update the user details.
        # The request includes the JSON content to patch.
        # The endpoint is constructed using the resource name and the user ID.
        # The JSON content is sent as part of the request parameters.
        # The response from the API is returned.

        obj = self.http_patch(endpoint=f"{self.ENDPOINT_NAME}/{pk}/", data=json_content)
        return obj

    def cmd_create(
        self,
        username: str,
        email: str = "",
        first_name: str = "",
        last_name: str = "",
        is_superuser: bool = False,
        is_staff: bool = False,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ):
        """
        creates an user with the given characteristics

        Args:
            username (str): username of the new user
            password (Optional[str]): password of the new user
            email (str): email of the new user
            first_name (str): first name of the new user
            last_name (str): last name of the new user
            is_superuser (bool): if true user will be a superuser
            is_staff (bool): if true user will be staff user
            fields (str): string of potential json object
            json_path (str): path to a json file
        """
        json_content = None
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

        obj = self.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_superuser=is_superuser,
            is_staff=is_staff,
            json_content=json_content,
            **kwargs,
        )
        print_json(obj)

    def create(
        self,
        username: str,
        email: str = "",
        first_name: str = "",
        last_name: str = "",
        is_superuser: bool = False,
        is_staff: bool = False,
        json_content: Optional[Dict] = None,
        **kwargs,
    ) -> Dict:
        """
        creates an user with the given characteristics

        Args:
            username (str): username of the new user
            password (Optional[str]): password of the new user
            email (str): email of the new user
            first_name (str): first name of the new user
            last_name (str): last name of the new user
            is_superuser (bool): if true user will be a superuser
            is_staff (bool): if true user will be staff user
            json_content (dict) dict object with addition metadata / fields
        """
        if json_content is None:
            json_content = {
                "username": username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            }
        return self.http_post(
            endpoint=self.ENDPOINT_NAME,
            params=json_content,
        )
