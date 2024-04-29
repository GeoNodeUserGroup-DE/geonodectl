from typing import Dict, Optional

from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey
from geonoderest.cmdprint import print_list_on_cmd, print_json


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
        if user_resources and user_groups:
            raise SystemExit(
                "user_resource and user_group cannot be active at the same time ..."
            )

        obj = self.get(
            pk, user_resources=user_resources, user_groups=user_groups, **kwargs
        )
        # in this case print as list of ressources
        if user_resources is True:
            print_list_on_cmd(obj, self.LIST_CMDOUT_HEADER)
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
                endpoint=f"{self.ENDPOINT_NAME}/{pk}/groups?page_size={kwargs['page_size']}"
            )
            return r
        elif user_resources is True:
            r = self.http_get(
                endpoint=f"{self.ENDPOINT_NAME}/{pk}/resources?page_size={kwargs['page_size']}"
            )
            return r
        else:
            r = self.http_get(
                endpoint=f"{self.ENDPOINT_NAME}/{pk}?page_size={kwargs['page_size']}"
            )
            return r[self.SINGULAR_RESOURCE_NAME]

    def cmd_create(
        self,
        username: str,
        password: Optional[str],
        email: str = "",
        first_name: str = "",
        last_name: str = "",
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
        """

        obj = self.create(title=title, extra_json_content=json_content, **kwargs)
        print_json(obj)
