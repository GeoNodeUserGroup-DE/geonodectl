from typing import List, Dict, Optional, TypeAlias, Callable, Any

import urllib3
import requests
import logging

from geonoderest.exceptions import GeoNodeRestException
from geonoderest.geonodetypes import GeonodeHTTPFile
from geonoderest.apiconf import GeonodeApiConf

urllib3.disable_warnings()

NetworkExceptionHandlingTypes: TypeAlias = (
    Callable[
        [
            "GeonodeRest",
            str,
            Dict,
            Dict,
            Optional[List[GeonodeHTTPFile]],
            Optional[int],
        ],
        Optional[Dict],
    ]  # http_post
    | Callable[
        ["GeonodeRest", str, Dict], Optional[Dict] | Optional[requests.Response]
    ]  # http_get_download, http_get
    | Callable[["GeonodeRest", str, Dict, Dict], Optional[Dict]]
)


class GeonodeRest(object):
    DEFAULTS = {"page_size": 100, "page": 1}

    def __init__(self, env: GeonodeApiConf):
        self.gn_credentials = env

    def __handle_http_params__(self, params: Dict, kwargs: Dict) -> Dict:
        """
        Internal method to handle pagination parameters.

        Parameters
        ----------
        params : Dict
            The dictionary of parameters to be updated.
        kwargs : Dict
            The dictionary of keyword arguments containing the pagination parameters.

        Returns
        -------
        Dict
            The updated dictionary of parameters.
        """
        if "page_size" in kwargs:
            params["page_size"] = kwargs["page_size"]
        if "page" in kwargs:
            params["page"] = kwargs["page"]

        if "filter" in kwargs and kwargs["filter"] is not None:
            for field, value in kwargs["filter"].items():
                field = "filter{" + field + "}"
                params[field] = value

        if "search" in kwargs and kwargs["search"] is not None:
            params["search"] = kwargs["search"]

        if "ordering" in kwargs and kwargs["ordering"] is not None:
            params["sort_by"] = kwargs["ordering"]

        return params

    @staticmethod
    def network_exception_handling(func: NetworkExceptionHandlingTypes):
        """
        Decorator to catch network related exceptions.

        This decorator is used to catch exceptions that could occur when making requests to the GeoNode API.
        If any of the handled exceptions occur, a GeoNodeRestException is raised with a meaningful error message.

        The handled exceptions are:
        - requests.exceptions.ConnectionError
        - urllib3.exceptions.MaxRetryError
        - ConnectionRefusedError

        The error message will give a hint about the cause of the exception and the potential solution.
        """

        def inner(*args, **kwargs):
            """
            Inner function of the network exception handling decorator.

            This function is wrapping the user's function to catch network related exceptions.
            If any of the handled exceptions occur, a GeoNodeRestException is raised with a
            meaningful error message.

            Parameters
            ----------
            *args
                The arguments to be passed to the function.
            **kwargs
                The keyword arguments to be passed to the function.

            Returns
            -------
            The return value of the wrapped function.
            """
            try:
                return func(*args, **kwargs)
            except requests.exceptions.ConnectionError:
                raise GeoNodeRestException(
                    "connection error: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODE_API_URL ..."
                )
            except urllib3.exceptions.MaxRetryError:
                raise GeoNodeRestException(
                    "max retries exceeded: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODE_API_URL ..."
                )
            except ConnectionRefusedError:
                raise GeoNodeRestException(
                    "connection refused: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODE_API_URL ..."
                )

        return inner

    @property
    def url(self):
        return str(self.gn_credentials.url)

    @property
    def header(self):
        return {"Authorization": f"Basic {self.gn_credentials.auth_basic}"}

    @property
    def verify(self):
        return self.gn_credentials.verify

    @network_exception_handling
    def http_post(
        self,
        endpoint: str,
        json: Dict = {},
        params: Dict = {},
        data: Dict = {},
        files: Optional[List[GeonodeHTTPFile]] = None,
        content_length: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        Execute http post on endpoint with params

        Args:
            endpoint (str): api endpoint
            files (List[GeonodeHTTPFile], optional): list of files to post.
            json (Dict, optional): json data to post
            params (Dict, optional): params dict provided with the post
            content_length (Optional[int], optional): content-length header for upload

        Raises:
            SystemExit: if bad http resonse raise SystemExit with logging

        Returns:
            Dict: returns response json
        """
        if content_length:
            self.header["content-length"] = content_length
        url = self.url + endpoint
        try:
            logging.debug(f"POST URL: {url}, headers: {self.header}, params: {params}, json: {json}, data: {data}")
            r = requests.post(
                url,
                headers=self.header,
                files=files,
                json=json,
                data=data,
                params=params,
                verify=self.verify,
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(err)
            return None
        return r.json()

    @network_exception_handling
    def http_get_download(
        self, url: str, params: Dict = {}
    ) -> Optional[requests.Response]:
        """raw get url

        Args:
            url (str): url to download

        Raises:
            SystemExit: if response code is bad exit

        Returns:
            object: returns downloaded data
        """
        try:
            logging.debug(f"GET URL: {url}, headers: {self.header}, params: {params}")
            r = requests.get(
                url, headers=self.header, params=params, verify=self.verify
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(err)
            return None
        return r

    @network_exception_handling
    def http_get(self, endpoint: str, params: Dict = {}) -> Optional[Dict]:
        """
        Execute HTTP GET request on the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the GET request to.
            params (Dict, optional): A dictionary of query parameters to include in the request.

        Raises:
            SystemExit: If a bad HTTP response is received, exits the program with logging.

        Returns:
            Dict: The JSON response from the server, or None if an error occurred.
        """

        url = self.url + endpoint
        try:
            logging.debug(f"GET URL: {url}, headers: {self.header}, params: {params}")
            r = requests.get(
                url, headers=self.header, params=params, verify=self.verify
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(err)
            return None
        return r.json()

    @network_exception_handling
    def http_patch(
        self, endpoint: str, json: Dict = {}, params: Dict = {}
    ) -> Optional[Dict]:
        """
        Execute HTTP PATCH request on the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the PATCH request to.
            json (Dict, optional): A dictionary of JSON data to include in the request body.
            params (Dict, optional): A dictionary of query parameters to include in the request.

        Raises:
            SystemExit: If a bad HTTP response is received, exits the program with logging.

        Returns:
            Dict: The JSON response from the server, or None if an error occurred.
        """
        url = self.url + endpoint
        try:
            logging.debug(f"PATCH URL: {url}, headers: {self.header}, params: {params}, json: {json}")
            r = requests.patch(
                url, headers=self.header, json=json, params=params, verify=self.verify
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(err)
            return None
        return r.json()

    @network_exception_handling
    def http_delete(
        self, endpoint: str, json: Dict = {}, params: Dict = {}
    ) -> Optional[Dict]:
        """
        Execute HTTP DELETE request on the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the DELETE request to.
            json (Dict, optional): A dictionary of JSON data to include in the request body.
            params (Dict, optional): A dictionary of query parameters to include in the request.

        Raises:
            SystemExit: If a bad HTTP response is received, exits the program with logging.

        Returns:
            Dict: The JSON response from the server, or None if an error occurred.
        """
        url = self.url + endpoint

        try:
            logging.debug(f"DELETE URL: {url}, headers: {self.header}, params: {params}, json: {json}")
            r = requests.delete(
                url, headers=self.header, params=params, json=json, verify=self.verify
            )
            r.raise_for_status()
            if r.status_code in [204]:
                return {}
        except requests.exceptions.HTTPError as err:
            logging.error(err)
            return None
        return r.json()
