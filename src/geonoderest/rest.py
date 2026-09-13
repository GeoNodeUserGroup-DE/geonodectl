from typing import List, Dict, Optional, TypeAlias, Callable, Any

import urllib3
import requests
import logging

from geonoderest.exceptions import (
    GeoNodeRestException,
    InvalidPkError,
    ResourceNotFoundError,
    UuidTypeMismatchError,
)
from geonoderest.geonodetypes import GeonodeHTTPFile
from geonoderest.apiconf import GeonodeApiConf
from geonoderest.identifier import (
    canonical_uuid,
    describe_resource_type,
    is_uuid,
    resource_type_matches,
)

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
    | Callable[
        ["GeonodeRest", str, Optional[str], Dict], requests.Response
    ]  # http_get_anonymous
)


def __response_json__(r: requests.Response) -> Optional[Dict]:
    """Parse a response body as JSON, reporting a non-JSON body as a failure.

    A proxy login page or an html error page served with 2xx would otherwise
    escape as a ``JSONDecodeError`` traceback - and since that is a ``ValueError``
    subclass it must not be mistaken for a usage error either (#151).
    """
    try:
        return r.json()
    except ValueError as e:
        logging.error(f"{r.url} did not return valid JSON: {e}")
        logging.debug(f"response body was: {r.text[:500]}")
        return None


def _normalised(value: str) -> Optional[str]:
    """Canonical form of ``value``, or None when it is not a uuid at all.

    Used only to compare what the API returned against what was asked for, so a
    malformed value has to come back as "does not match" rather than raising.
    """
    try:
        return canonical_uuid(value)
    except (ValueError, AttributeError, TypeError):
        return None


class GeonodeRest(object):
    DEFAULTS = {"page_size": 100, "page": 1}

    #: ``resource_type`` the objects this handler addresses are, used to check a
    #: uuid names the right kind of object. ``ANY_RESOURCE_TYPE`` accepts every
    #: resource type; ``None`` means these objects have no uuid at all - users
    #: and groups are not ``ResourceBase``, so they stay pk-only (#160).
    UUID_RESOURCE_TYPE: Optional[str] = None

    def __init__(self, env: GeonodeApiConf):
        self.gn_credentials = env

    def __resolve_identifier__(self, identifier, expected: Optional[str] = None) -> int:
        """Return the pk named by ``identifier``, which may be a pk or a uuid.

        A pk costs nothing - it is returned as-is. A uuid costs exactly one GET:
        there is no uuid route on the GeoNode API (no viewset overrides
        ``lookup_field``), so a uuid is reachable only as a list filter, and the
        row it returns carries ``resource_type`` for the type check.

        Args:
            identifier: a pk (int or digit string) or a resource uuid
            expected (Optional[str]): resource_type the uuid must name; defaults
                to this handler's ``UUID_RESOURCE_TYPE``. Pass it when an
                argument names a different kind of object than the handler does -
                ``maps maplayers add`` takes *dataset* identifiers, for instance.

        Raises:
            InvalidPkError: not a pk and not a uuid, or a uuid was given for an
                object type that has none
            UuidTypeMismatchError: the uuid names a different kind of object
            ResourceNotFoundError: no object has that uuid
        """
        if isinstance(identifier, int):
            return identifier

        value = str(identifier)
        if value.isdigit():
            return int(value)

        if not is_uuid(value):
            raise InvalidPkError(
                f"Invalid identifier {value}, is neither a pk nor a uuid ..."
            )

        if expected is None:
            expected = self.UUID_RESOURCE_TYPE
        if expected is None:
            raise InvalidPkError(
                f"{self.__class__.__name__} objects are identified by pk, "
                f"not by uuid: {value}"
            )

        # the filter is an exact match, so send the canonical spelling
        wanted = canonical_uuid(value)

        # advertised=all because AdvertisedFilter applies to list but is skipped
        # on retrieve - without it a non-advertised resource would be invisible
        # here while GET resources/<pk> still returns it, making a uuid lookup
        # narrower than the direct fetch it stands in for
        r = self.http_get(
            endpoint="resources/",
            params={"filter{uuid}": wanted, "advertised": "all"},
        )
        if r is None:
            raise GeoNodeRestException(f"could not look up uuid {value} ...")

        resources = r.get("resources") or []
        if not resources:
            raise ResourceNotFoundError(f"no resource found with uuid {value} ...")

        resource = resources[0]
        # never trust the first row blindly: if the filter were ever dropped - a
        # proxy stripping the brace syntax, an older filter backend - this would
        # otherwise resolve to an arbitrary resource and act on the wrong object
        returned = resource.get("uuid")
        if returned is not None and _normalised(str(returned)) != wanted:
            raise ResourceNotFoundError(
                f"uuid lookup for {value} returned {returned} instead - "
                "the API ignored the uuid filter ..."
            )

        actual = resource.get("resource_type") or ""
        if not resource_type_matches(actual, expected):
            raise UuidTypeMismatchError(
                f"uuid {value} is a {actual or 'resource of unknown type'}, "
                f"not a {describe_resource_type(expected)} ..."
            )

        pk = resource.get("pk")
        if pk is None:
            raise GeoNodeRestException(
                f"uuid {value} resolved to a resource without a pk ..."
            )
        # the API serializes pk as a string
        return int(pk)

    def __resolve_identifiers__(
        self, identifiers, expected: Optional[str] = None
    ) -> List[int]:
        """Resolve a list of pks/uuids, in order. See __resolve_identifier__."""
        return [self.__resolve_identifier__(i, expected) for i in identifiers or []]

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

        Returns:
            Optional[Dict]: the response json, or None when the request failed -
                a bad http response is logged rather than raised
        """
        if content_length:
            self.header["content-length"] = content_length
        url = self.url + endpoint
        try:
            logging.debug(
                f"POST URL: {url}, headers: {self.header}, params: {params}, json: {json}, data: {data}"
            )
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
            if r is not None:
                logging.error(f"POST error response: {r.text}")
            logging.error(err)
            return None
        return __response_json__(r)

    @network_exception_handling
    def http_get_download(
        self, url: str, params: Dict = {}
    ) -> Optional[requests.Response]:
        """raw get url

        Args:
            url (str): url to download

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
            if r is not None:
                logging.error(f"GET error response: {r.text}")
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
            if r is not None:
                logging.error(f"GET error response: {r.text}")
            logging.error(err)
            return None
        return __response_json__(r)

    @network_exception_handling
    def http_put(
        self, endpoint: str, json_content: Dict = {}, params: Dict = {}, **kwargs
    ) -> Optional[Dict]:
        """
        Execute HTTP PUT request on the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the PUT request to.
            json_content (Dict, optional): A dictionary of JSON data to include in the request body.
            params (Dict, optional): A dictionary of query parameters to include in the request.

        Returns:
            Dict: The JSON response from the server, or None if an error occurred.
        """
        url = self.url + endpoint
        try:
            logging.debug(
                f"PUT URL: {url}, headers: {self.header}, params: {params}, json: {json_content}"
            )
            r = requests.put(
                url,
                headers=self.header,
                json=json_content,
                params=params,
                verify=self.verify,
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if r is not None:
                logging.error(f"PUT error response: {r.text}")
            logging.error(err)
            return None
        return __response_json__(r)

    @network_exception_handling
    def http_get_anonymous(
        self,
        endpoint: str = "",
        url: Optional[str] = None,
        params: Dict = {},
    ) -> requests.Response:
        """
        Execute an HTTP GET without sending session credentials.

        Useful for probes that must verify the API behavior for unauthenticated
        callers — e.g. confirming a permission restriction prevents anonymous
        reads. No Authorization header, no session cookie. Returns the raw
        `requests.Response` so callers can inspect status code, headers, and
        body; HTTP error statuses are NOT raised because they are frequently
        the expected outcome.

        Args:
            endpoint (str): Endpoint relative to the configured API base URL.
                Ignored when `url` is provided.
            url (Optional[str]): Absolute URL to GET. Takes precedence over
                `endpoint`.
            params (Dict): Query-string parameters.

        Returns:
            requests.Response: The raw response.
        """
        target_url = url if url else self.url + endpoint
        logging.debug(f"GET (anonymous) URL: {target_url}, params: {params}")
        return requests.get(target_url, params=params, verify=self.verify)

    @network_exception_handling
    def http_patch(
        self, endpoint: str, json_content: Dict = {}, params: Dict = {}, **kwargs
    ) -> Optional[Dict]:
        """
        Execute HTTP PATCH request on the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the PATCH request to.
            json (Dict, optional): A dictionary of JSON data to include in the request body.
            params (Dict, optional): A dictionary of query parameters to include in the request.

        Returns:
            Dict: The JSON response from the server, or None if an error occurred.
        """
        url = self.url + endpoint
        try:
            logging.debug(
                f"PATCH URL: {url}, headers: {self.header}, params: {params}, json: {json_content}"
            )
            r = requests.patch(
                url,
                headers=self.header,
                json=json_content,
                params=params,
                verify=self.verify,
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if r is not None:
                logging.error(f"PATCH error response: {r.text}")
            logging.error(err)
            return None
        return __response_json__(r)

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

        Returns:
            Dict: The JSON response from the server, or None if an error occurred.
        """
        url = self.url + endpoint

        try:
            logging.debug(
                f"DELETE URL: {url}, headers: {self.header}, params: {params}, json: {json}"
            )
            r = requests.delete(
                url, headers=self.header, params=params, json=json, verify=self.verify
            )
            r.raise_for_status()
            if r.status_code in [204]:
                return {}
        except requests.exceptions.HTTPError as err:
            if r is not None:
                logging.error(f"DELETE error response: {r.text}")
            logging.error(err)
            return None
        return __response_json__(r)
