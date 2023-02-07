
from src.cmdprint import show_list
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from abc import abstractmethod
import requests
import urllib3
urllib3.disable_warnings()


@dataclass
class GeonodeEnv:
    url: str
    auth_basic: str
    verify: bool


class GeoNodeObject:

    DEFAULT_LIST_KEYS = [{'type': list, 'key': 'pk'}],
    DEFAULT_UPLOAD_KEYS = ["key", "value"]

    RESOURCE_TYPE = ""

    def __init__(self, env: GeonodeEnv):
        self.gn_credentials = env

    @property
    def url(self):
        return str(self.gn_credentials.url)

    @property
    def header(self):
        return {'Authorization': f'Basic {self.gn_credentials.auth_basic}'}

    @property
    def verify(self):
        return self.gn_credentials.verify

    def http_post(self,
                  endpoint: str,
                  files: Optional[List[Tuple]] = None,
                  params: Optional[Dict] = None,
                  content_length: Optional[int] = None
                  ):

        if content_length:
            self.header['content-length'] = content_length
        url = self.url + endpoint

        try:
            r = requests.post(url, headers=self.header,
                              files=files, data=params, verify=self.verify)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        return r.json()

    def http_get_download(self, url: str) -> object:
        """ raw get url

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

    def http_get(self,
                 endpoint: str,
                 params: Dict = None
                 ) -> Dict:
        """ execute http delete on endpoint with params

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
            r = requests.get(url, headers=self.header,
                             data=params, verify=self.verify)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

        return r.json()

    def http_delete(self, endpoint: str, params: Dict = {}) -> Dict:
        """ execute http delete on endpoint with params

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

    def cmd_list(self, *args, **kwargs):
        """ show list of geonode obj on the cmdline """
        obj = self.list(**kwargs)
        if kwargs['json']:
            import pprint
            pprint.pprint(obj)
        else:
            self.print_list_on_cmd(obj)

    def list(self, *args, **kwargs) -> Dict:
        """ returns dict of datasets from geonode

        Returns:
            Dict: request response
        """
        r = self.http_get(
            endpoint=f"{self.RESOURCE_TYPE}/?page_size={kwargs['page_size']}")
        return r[self.RESOURCE_TYPE]

    def cmd_delete(self, *args, **kwargs):
        self.delete(**kwargs)
        print("deleted ...")

    def delete(self, *args, **kwargs):
        """ delete geonode resource object"""
        pk = kwargs['pk']
        self.http_get(endpoint=f"{self.RESOURCE_TYPE}/{pk}")
        self.http_delete(endpoint=f"resources/{pk}/delete")

    @abstractmethod
    def cmd_patch(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def patch(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def cmd_upload(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def upload(self, *args, **kwargs):
        raise NotImplementedError

    def cmd_metadata(self, *args, **kwargs):
        metadata = self.metadata(**kwargs)
        print(metadata.text)

    def metadata(self, *args, **kwargs):
        pk = kwargs['pk']
        r = self.http_get(endpoint=f"resources/{pk}")['resource']

        link: str = ""
        try:
            link = [m for m in r['links'] if m['name']
                    == kwargs['metadata_type']][0]["url"]
        except KeyError:
            SystemExit(
                f"Could not find requested metadata type: {kwargs['metadata_type']}")
        metadata = self.http_get_download(link)
        return metadata

    @property
    def cmd_list_header(self) -> List[str]:
        """returns the default header to print list on cmd

        Returns:
            List[str]: list of header elements as str
        """
        return [e['key'] if list == e['type'] else ".".join(e['key']) for e in self.DEFAULT_LIST_KEYS]

    def print_list_on_cmd(self, ds: Dict):
        """print a beautiful list on the cmdline

        Args:
            ds (Dict): dict object to print on cmd line
        """
        def generate_line(i, ds: Dict, headers: List[Dict]) -> List:
            return [ds[i][e['key']] if list == e['type'] else ds[i][e['key'][0]][e['key'][1]] for e in headers]

        values = [generate_line(i, ds, self.DEFAULT_LIST_KEYS)
                  for i in range(len(ds))]
        show_list(headers=self.cmd_list_header, values=values)
