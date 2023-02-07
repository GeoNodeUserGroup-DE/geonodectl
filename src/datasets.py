
import os
from pathlib import Path

from src.geonodeobject import GeoNodeObject
from src.cmdprint import show_list


class GeonodeDatasets(GeoNodeObject):

    DEFAULT_LIST_KEYS = [{'type': list, 'key': 'pk'},
                         {'type': list, 'key': 'title'},
                         {'type': dict, 'key': ['owner', 'username']},
                         {'type': list, 'key': 'date'},
                         {'type': list, 'key': 'is_approved'},
                         {'type': list, 'key': 'is_published'},
                         {'type': list, 'key': 'state'},
                         {'type': list, 'key': 'detail_url'}]

    RESOURCE_TYPE = "datasets"

    def cmd_upload(self,
                   charset: str = "UTF-8",
                   time: bool = False,
                   *args,
                   **kwargs):
        """ upload data and show them on the cmdline

        Args:
            charset (str, optional): charset of data Defaults to "UTF-8".
            time (bool, optional): set if data is timeseries data Defaults to False.
        """
        r = self.upload(charset=charset,
                        time=time,
                        *args,
                        **kwargs)
        if kwargs['json'] is True:
            import pprint
            pprint.pprint(r)
        else:
            list_items = [
                ["title", kwargs['title']],
                ["success", str(r['success'])],
                ["status", r['status']],
                ["bbox", r['bbox'] if 'bbox' in r else ""],
                ["crs", r['crs'] if 'crs' in r else ""],
                ["url", r['url'] if 'url' in r else ""]
            ]
            show_list(values=list_items, headers=["key", "value"])

    def upload(self,
               charset: str = "UTF-8",
               time: bool = False,
               mosaic: bool = False,
               *args,
               **kwargs):
        """Upload dataset to geonode.

        Args:
            filepath_path (Path): Path to the file to upload. If shape make sure to set
                  the shp file and add place other files with same name next to the given
            title (str): title of the new dataset
            charset (str, optional): Fileencoding Defaults to "UTF-8".
            non_interactive (bool, optional): False if dataset is interactive. Defaults to True.
            time (bool, optional): True if the dataset is a timeseries dataset. Defaults to False.

        Raises:
            FileNotFoundError: raised when given file is not found
        """
        dataset_path = kwargs['file_path']

        # handle shape files different
        if dataset_path.suffix == '.shp':
            dbf_file = Path(os.path.join(
                dataset_path.parent, dataset_path.stem + ".dbf"))
            shx_file = Path(os.path.join(
                dataset_path.parent, dataset_path.stem + ".shx"))
            prj_file = Path(os.path.join(
                dataset_path.parent, dataset_path.stem + ".prj"))

            if not any(x.exists for x in [dataset_path, dbf_file, shx_file, prj_file]):
                raise FileNotFoundError

            content_length = sum([os.path.getsize(f) for f in [
                                 dataset_path, dbf_file, shx_file, prj_file]])

            files = [
                ('base_file', (dataset_path.name, open(
                    dataset_path, 'rb'), 'application/octet-stream')),
                ('dbf_file', (dbf_file.name, open(
                    dbf_file, 'rb'), 'application/octet-stream')),
                ('shx_file', (shx_file.name, open(
                    shx_file, 'rb'), 'application/octet-stream')),
                ('prj_file', (prj_file.name, open(
                    prj_file, 'rb'), 'application/octet-stream')),
            ]

        else:
            if not dataset_path.exists():
                raise FileNotFoundError
            content_length = os.path.getsize(dataset_path)

            files = [
                ('base_file', (dataset_path.name, open(dataset_path), 'rb')),
            ]

        params = {
            # layer permissions
            "permissions": '{ "users": {"AnonymousUser": ["view_resourcebase"]} , "groups":{}}',
            "dataset_title": kwargs['title'],
            "abstract": kwargs['abstract'] if 'abstract' in kwargs else '',
            "mosaic": mosaic,
            "time": str(time),
            "charset": charset,
            "non_interactive": True
        }

        return self.http_post(endpoint="uploads/upload",
                              files=files,
                              params=params,
                              content_length=content_length,
                              )

    def cmd_show(self, *args, **kwargs):
        raise NotImplementedError

    def get(self, *args, **kwargs):
        raise NotImplementedError

    def update_dataset(resource_id, metadata, headers):
        raise NotImplementedError
        # tes = datetime.datetime.strptime(metadata['Start Date'], '%d.%m.%Y').strftime("%Y-%m-%dT%H:%M")

        # url = f"https://geonode.corki.bonares.de/api/v2/datasets/{resource_id}/"
        # params = {
        #     # metadata to ignore:
        #     # 'Name': html filename
        #     # 'Citation'
        #     # 'ShowOnMap',
        #     # 'Raumelement',
        #     # 'ID',: ORD ID
        #     # 'Geolocation', Geo
        #     # 'RelatedIdentifier',
        #     # 'ResourceType': e.g. Table
        #     #  metadata["Created"], hard in geonoide
        #     # "last_updated": metadata["Modified"], hard in geonode
        #     'title': metadata["Title"],
        #     'abstract': metadata['Summary'],
        #     'doi': metadata["DigitalObjectIdentifier"],

        #     # "date": metadata["PublicationYear"], datetype = published

        #     'temporal_extent_start': tes,

        #     # Authors: must be found in ZALF LDAP
        #     # 'Subjects', Agrovoc keywords
        #     # 'Contributors', New Contact roles institutions
        #     # 'Rights': legal rights - Restrictions mapping

        #     # 'Attribution': TODO,
        #     # 'data_quality_statement':  TODO,
        #     # 'constraints_other': TODO,
        #     # 'edition": TODO,
        #     # 'purpose': TODO,
        #     # ' Supplemental information': TODO,
        #     # 'maintenance_frequency': TODO,
        #     # attributes

        #     # 'category': 'farming',
        #     'language': "eng",
        #     # 'regions': "DE"
        # }
        # ds_patched_resp = requests.request("PATCH", url, headers=headers, data=params, verify=False)

        # if ds_patched_resp.status_code != 200:
        #   logging.error(f"update dataset [{name}] failed ...")
