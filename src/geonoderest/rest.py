from typing import List, Dict, Optional, TypeAlias, Callable, Any

import json
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

    def _format_error_payload(self, response: Optional[requests.Response]) -> str:
        if response is None:
            return ""

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            if "detail" in payload and isinstance(payload["detail"], (str, int, float)):
                return str(payload["detail"])
            if "errors" in payload:
                return json.dumps(payload["errors"], ensure_ascii=False)
            return json.dumps(payload, ensure_ascii=False)

        if isinstance(payload, list):
            return json.dumps(payload, ensure_ascii=False)

        if response.text:
            return response.text.strip()

        return ""

    def _raise_http_exception(
        self,
        method: str,
        url: str,
        response: Optional[requests.Response],
        err: requests.exceptions.HTTPError,
    ) -> None:
        status_part = ""
        detail_part = ""
        final_url = url

        if response is not None:
            status_code = getattr(response, "status_code", None)
            reason = getattr(response, "reason", "")
            if status_code is not None:
                status_part = f" with status {status_code} {reason}".rstrip()
            detail = self._format_error_payload(response)
            if detail:
                detail_part = f": {detail}"
            final_url = getattr(response, "url", url)

        message = f"{method} {final_url}{status_part}{detail_part}".strip()
        logging.error(message)
        raise GeoNodeRestException(message) from err

    @network_exception_handling
    def http_post(
        self,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        files: Optional[List[GeonodeHTTPFile]] = None,
        content_length: Optional[int] = None,
        timeout: int = 60,
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
        logging.debug(
            f"POST URL: {url}, headers: {self.header}, params: {params}, json: {json}, data: {data}"
        )
        response: Optional[requests.Response] = None
        try:
            response = requests.post(
                url,
                headers=self.header,
                files=files,
                json=json,
                data=data or {},
                params=params or {},
                verify=self.verify,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self._raise_http_exception("POST", url, response, err)
            return None
        return response.json()

    @network_exception_handling
    def http_get_download(
        self, url: str, params: Optional[Dict] = None, timeout: int = 60
    ) -> Optional[requests.Response]:
        """raw get url

        Args:
            url (str): url to download

        Raises:
            SystemExit: if response code is bad exit

        Returns:
            object: returns downloaded data
        """
        logging.debug(f"GET URL: {url}, headers: {self.header}, params: {params}")
        response: Optional[requests.Response] = None
        try:
            response = requests.get(
                url,
                headers=self.header,
                params=params or {},
                verify=self.verify,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self._raise_http_exception("GET", url, response, err)
        assert response is not None
        return response

    @network_exception_handling
    def http_get(
        self, endpoint: str, params: Optional[Dict] = None, timeout: int = 60
    ) -> Optional[Dict]:
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
        logging.debug(f"GET URL: {url}, headers: {self.header}, params: {params}")
        response: Optional[requests.Response] = None
        try:
            response = requests.get(
                url,
                headers=self.header,
                params=params or {},
                verify=self.verify,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self._raise_http_exception("GET", url, response, err)
        assert response is not None
        return response.json()

    @network_exception_handling
    def http_patch(
        self,
        endpoint: str,
        json_content: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 60,
        **kwargs,
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
        logging.debug(
            f"PATCH URL: {url}, headers: {self.header}, params: {params}, json: {json_content}"
        )
        response: Optional[requests.Response] = None
        try:
            response = requests.patch(
                url,
                headers=self.header,
                json=json_content,
                params=params or {},
                verify=self.verify,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self._raise_http_exception("PATCH", url, response, err)
        assert response is not None
        return response.json()

    @network_exception_handling
    def http_delete(
        self,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 60,
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

        logging.debug(
            f"DELETE URL: {url}, headers: {self.header}, params: {params}, json: {json}"
        )
        response: Optional[requests.Response] = None
        try:
            response = requests.delete(
                url,
                headers=self.header,
                params=params or {},
                json=json,
                verify=self.verify,
                timeout=timeout,
            )
            response.raise_for_status()
            if response.status_code in [204]:
                return {}
        except requests.exceptions.HTTPError as err:
            self._raise_http_exception("DELETE", url, response, err)
        assert response is not None
        return response.json()
