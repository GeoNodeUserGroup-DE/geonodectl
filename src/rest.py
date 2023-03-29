from typing import List, Dict, Optional
import requests
import urllib3
from src.geonodetypes import GeonodeEnv, GeonodeHTTPFile

urllib3.disable_warnings()


class GeonodeRest(object):
    def __init__(self, env: GeonodeEnv):
        self.gn_credentials = env

    @property
    def url(self):
        return str(self.gn_credentials.url)

    @property
    def header(self):
        return {"Authorization": f"Basic {self.gn_credentials.auth_basic}"}

    @property
    def verify(self):
        return self.gn_credentials.verify

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

    def http_get_download(self, url: str) -> requests.models.Response:
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
        return r

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
