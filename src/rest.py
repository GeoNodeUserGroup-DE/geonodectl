from typing import List, Dict, Optional
import urllib3
import requests
from src.geonodetypes import GeonodeEnv, GeonodeHTTPFile, NetworkExceptionHandlingTypes

urllib3.disable_warnings()


class GeonodeRest(object):
    def __init__(self, env: GeonodeEnv):
        self.gn_credentials = env

    @staticmethod
    def network_exception_handling(func: NetworkExceptionHandlingTypes):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.ConnectionError:
                raise SystemExit(
                    "connection error: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODECTL_URL ..."
                )
            except urllib3.exceptions.MaxRetryError:
                raise SystemExit(
                    "max retries exceeded: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODECTL_URL ..."
                )
            except ConnectionRefusedError:
                raise SystemExit(
                    "connection refused: Could not reach geonode api. please check if the endpoint up and available, "
                    "check also the env variable: GEONODECTL_URL ..."
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
            params (Dict, optional): parameter to pust. Defaults to {}.
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
            r = requests.get(url, headers=self.header, json=params, verify=self.verify)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        return r.json()

    @network_exception_handling
    def http_patch(self, endpoint: str, params: Dict = {}) -> Dict:
        """execute http patch on endpoint with params

        Args:
            endpoint (str): api endpoint
            params (Dict, optional):  params dict provided with the delete

        Raises:
              SystemExit: if bad http resonse raise SystemExit with logging

        Returns:
            Dict: returns response json
        """
        url = self.url + endpoint
        try:
            r = requests.patch(
                url, headers=self.header, json=params, verify=self.verify
            )
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
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
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

        return r.json()
