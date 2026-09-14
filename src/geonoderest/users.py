import logging
from typing import Dict, List, Optional

from geonoderest.resources import GeonodeResourceHandler
from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey
from geonoderest.exceptions import (
    GeoNodeRestException,
    GeonodeUsageError,
    MissingArgumentError,
)
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.jsonsource import JsonSourceError, load_json_source
from geonoderest.cmdprint import (
    print_list_on_cmd,
    print_json,
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
    ) -> int:
        """show requested user in detail on cmd. Further show groups or accessable items of user

        Args:
            pk (int): id of user to show in detail
            user_resources (bool, optional): if set to true ressources accessable
                                             by given user are listed. Defaults to False.
            user_groups (bool, optional): if set to true groups of given user are printed.
                                          Defaults to False.

        Raises:
            AttributeError: if user_resources and user_groups are both true this function gets confused
        """

        obj = self.get(
            pk, user_resources=user_resources, user_groups=user_groups, **kwargs
        )
        if obj is None:
            logging.error("describe user failed ... ")
            return EXIT_FAILED
        if user_resources is True:
            print_list_on_cmd(
                obj["resources"], GeonodeResourceHandler.LIST_CMDOUT_HEADER
            )
        else:
            print_json(obj)
        return EXIT_OK

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
        params = self.__handle_http_params__({}, kwargs)

        if user_groups is True:
            r = self.http_get(endpoint=f"{self.ENDPOINT_NAME}/{pk}/groups")
            return r
        elif user_resources is True:
            endpoint = f"{GeonodeResourceHandler.ENDPOINT_NAME}"
            r = self.http_get(endpoint=endpoint, params=params)
            return r
        else:
            r = self.http_get(
                endpoint=f"{self.ENDPOINT_NAME}/{pk}",
                params=params,
            )
            if r is None:
                return None
            return r[self.SINGULAR_RESOURCE_NAME]

    def cmd_patch(
        self,
        pk: int,
        fields: Optional[str] = None,  # JSON string
        json_path: Optional[str] = None,  # Path to a JSON file, or a url serving one
        **kwargs,
    ) -> int:
        """Patch user details and print the result.

        Args:
            pk (int): User ID.
            fields (Optional[str]): JSON string. Defaults to None.
            json_path (Optional[str]): Path to a JSON file, or a http(s) url
                serving one. Defaults to None.
            kwargs: Additional keyword arguments.

        Returns:
            int: EXIT_OK, EXIT_FAILED when the patch was rejected, or
                EXIT_USAGE when no readable json was given
        """
        if not (json_path or fields):
            logging.error("At least one of 'fields' or 'json_path' must be provided.")
            return EXIT_USAGE
        try:
            json_content = load_json_source(json_path=json_path, fields=fields)
        except JsonSourceError as e:
            logging.error(str(e))
            return EXIT_USAGE

        if json_content is None:
            logging.error("At least one of 'fields' or 'json_path' must be provided.")
            return EXIT_USAGE

        # Apply patch and print result
        obj = self.patch(pk=pk, json_content=json_content, **kwargs)
        if obj is None:
            logging.error(f"patching user {pk} failed ... ")
            return EXIT_FAILED
        print_json(obj)
        return EXIT_OK

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

        obj = self.http_patch(
            endpoint=f"{self.ENDPOINT_NAME}/{pk}/", json_content=json_content
        )
        return obj

    def cmd_create(
        self,
        username: Optional[str] = None,
        email: str = "",
        first_name: str = "",
        last_name: str = "",
        is_superuser: bool = False,
        is_staff: bool = False,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ) -> int:
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
            json_path (str): path to a json file, or a http(s) url serving one

        Returns:
            int: EXIT_OK, EXIT_FAILED when the API rejected the new user, or
                EXIT_USAGE when the input json or the username was missing
        """
        json_content = None
        if json_path or fields:
            try:
                json_content = load_json_source(json_path=json_path, fields=fields)
            except JsonSourceError as e:
                logging.error(str(e))
                return EXIT_USAGE

        try:
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
        except GeonodeUsageError as e:
            logging.error(str(e))
            return EXIT_USAGE
        if obj is None:
            logging.error("user creation failed ... ")
            return EXIT_FAILED
        print_json(obj)
        return EXIT_OK

    def create(
        self,
        username: Optional[str] = None,
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
            if username is None:
                # library method: raise so the caller decides, see #69
                raise MissingArgumentError("missing username for user creation ...")

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
            json=json_content,
        )

    def delete(self, pk: int, **kwargs):
        """delete geonode resource object

        Returns the API response, like every other ``delete()`` - ``cmd_delete``
        reads ``None`` as failure, so swallowing it reported every successful
        deletion as a failure.
        """
        self.http_get(endpoint=f"{self.ENDPOINT_NAME}/{pk}")
        return self.http_delete(endpoint=f"users/{pk}")

    def cmd_transfer_resources(
        self,
        pk: int,
        new_owner: int,
        resources=None,
        **kwargs,
    ) -> int:
        """hand resources of a user over to another user and print the result

        Args:
            pk (int): id of the user currently owning the resources
            new_owner (int): id of the user to hand them to
            resources (optional): pks or uuids of the resources to move,
                                  all of the users resources if left out

        Returns:
            int: EXIT_OK, or EXIT_FAILED when the transfer was rejected
        """
        # users have no uuid, but the resources they own do
        if resources is not None:
            resources = GeonodeResourceHandler(
                env=self.gn_credentials
            ).__resolve_identifiers__(resources)
        obj = self.transfer_resources(
            pk=pk, new_owner=new_owner, resources=resources, **kwargs
        )
        if obj is None:
            logging.error(f"transferring resources of user {pk} failed ... ")
            return EXIT_FAILED
        print_json(obj)
        return EXIT_OK

    def transfer_resources(
        self,
        pk: int,
        new_owner: int,
        resources: Optional[List[int]] = None,
        **kwargs,
    ) -> Optional[Dict]:
        """hand resources of a user over to another user

        Two shapes of this endpoint are in the wild. GeoNode 5 takes newOwner,
        currentOwner and an optional list of resource ids; GeoNode 4.4 takes a
        single `owner` and always moves every resource the user owns. The
        modern payload is sent first and the legacy one only after GeoNode has
        answered that it did not understand it.

        Note that `resources` is always sent, empty for a whole-account
        transfer: GeoNode 5 raises a TypeError on a JSON body that leaves it
        out entirely.

        Args:
            pk (int): id of the user currently owning the resources
            new_owner (int): id of the user to hand them to
            resources (Optional[List[int]]): ids of the resources to move,
                                             all of the users resources if left out

        Raises:
            GeoNodeRestException: if a subset was asked for but the GeoNode
                                  only offers the whole-account transfer

        Returns:
            Optional[Dict]: the API response, or None if the transfer failed
        """
        endpoint = f"{self.ENDPOINT_NAME}/{pk}/transfer_resources"
        obj = self.http_post(
            endpoint=endpoint,
            json={
                "newOwner": new_owner,
                "currentOwner": pk,
                "resources": resources or [],
            },
        )
        if obj is not None:
            return obj

        if resources:
            raise GeoNodeRestException(
                "could not transfer the given resources. On GeoNode 4.4 this endpoint moves "
                "every resource of the user and cannot be given a subset ..."
            )
        logging.info("retrying with the GeoNode 4.4 payload ...")
        return self.http_post(endpoint=endpoint, json={"owner": new_owner})
