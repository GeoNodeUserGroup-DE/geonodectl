from typing import List, Dict, Optional, TypeAlias, Callable, Any

import urllib3
import requests
import logging

from geonoderest.geonodetypes import GeonodeHTTPFile
from geonoderest.apiconf import GeonodeApiConf

urllib3.disable_warnings()


NetworkExceptionHandlingTypes: TypeAlias = (
    Callable[["GeonodeRest", str, Dict[Any, Any]], Dict[Any, Any]]
    | Callable[["GeonodeRest", str], Dict[Any, Any]]
)


class GeonodeRest(object):
    DEFAULTS = {"page_size": 100, "page": 1}

    def __init__(self, env: GeonodeApiConf):
        self.gn_credentials = env

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

    @staticmethod
    def network_exception_handling(func: NetworkExceptionHandlingTypes):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.ConnectionError:
                raise SystemExit(
                    "connection error: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODE_API_URL ..."
                )
            except urllib3.exceptions.MaxRetryError:
                raise SystemExit(
                    "max retries exceeded: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODE_API_URL ..."
                )
            except ConnectionRefusedError:
                raise SystemExit(
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
        files: Optional[List[GeonodeHTTPFile]] = None,
        params: Dict = {},
        content_length: Optional[int] = None,
    ) -> Dict:
        """http post to geonode endpoint

        Args:
            endpoint (str): api endpoint
            files (Optional[List[GeonodeHTTPFile]], optional): files to post. Defaults to None.
            params (Dict, optional): parameter to post. Defaults to {}.
            content_length (Optional[int], optional): optional content length
                      sometimes its useful to set by yourself. Defaults to None.

        Raises:
            SystemExit: if http status is not 200

        Returns:
            Dict: post response
        """
        if content_length:
            self.header["content-length"] = content_length
        url = self.url + endpoint

        try:
            r = requests.post(
                url, headers=self.header, files=files, json=params, verify=self.verify
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(r.json())
            raise SystemExit(err)
        return r.json()

    @network_exception_handling
    def http_get_download(self, url: str) -> Dict:
        """raw get url

        Args:
            url (str): url to download

        Raises:
            SystemExit: if response code is bad exit

        Returns:
            object: returns downloaded data
        """
        try:
            r = requests.get(url, headers=self.header, verify=self.verify)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(r.json())
            raise SystemExit(err)
        return r.json()

    @network_exception_handling
    def http_get(self, endpoint: str, params: Dict = {}) -> Dict:
        """execute http delete on endpoint with params

        Args:
            endpoint (str):  api endpoint
            params (Dict, optional):params dict provided with the get

        Raises:
            SystemExit: if bad http resonse raise SystemExit with logging

        Returns:
            Dict: returns response json
        """
        url = self.url + endpoint
        try:
            r = requests.get(
                url, headers=self.header, params=params, verify=self.verify
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        return r.json()

    @network_exception_handling
    def http_patch(self, endpoint: str, data: Dict = {}) -> Dict:
        """execute http patch on endpoint with params

        Args:
            endpoint (str): api endpoint
            data (Dict, optional):  params dict with data to patch

        Raises:
              SystemExit: if bad http resonse raise SystemExit with logging

        Returns:
            Dict: returns response json
        """
        url = self.url + endpoint
        try:
            r = requests.patch(url, headers=self.header, json=data, verify=self.verify)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logging.error(r.text)
            raise SystemExit(err)
        return r.json()

    @network_exception_handling
    def http_delete(self, endpoint: str, params: Dict = {}) -> Dict:
        """execute http delete on endpoint with params

        Args:
            endpoint (str): api endpoint
            params (Dict, optional): params dict provided with the delete

        Raises:
            SystemExit: if bad http resonse raise SystemExit with logging

        Returns:
            Dict: returns response json
        """
        url = self.url + endpoint

        try:
            r = requests.delete(url, headers=self.header, verify=self.verify)
            r.raise_for_status()
            if r.status_code in [204]:
                return {}
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        return r.json()
