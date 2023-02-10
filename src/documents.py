
import os
import mimetypes
from pathlib import Path
from typing import List, Optional
from src.geonodeobject import GeoNodeObject, GeonodeCmdOutListKey, GeonodeCmdOutDictKey, GeonodeHTTPFile
from src.cmdprint import show_list


class GeonodeDocuments(GeoNodeObject):

    DEFAULT_LIST_KEYS = [
        GeonodeCmdOutListKey(key='pk'),
        GeonodeCmdOutListKey(key='title'),
        GeonodeCmdOutDictKey(key=['owner', 'username']),
        GeonodeCmdOutListKey(key='date'),
        GeonodeCmdOutListKey(key="is_approved"),
        GeonodeCmdOutListKey(key="is_published"),
        GeonodeCmdOutListKey(key='resource_type'),
        GeonodeCmdOutListKey(key='detail_url')
    ]

    RESOURCE_TYPE = "documents"

    def cmd_upload(self,
                   charset: str = "UTF-8",
                   time: bool = False,
                   **kwargs):
        """ upload data and show them on the cmdline

        Args:
            charset (str, optional): charset of data Defaults to "UTF-8".
            time (bool, optional): set if data is timeseries data Defaults to False.
        """
        r = self.upload(charset=charset,
                        time=time,
                        **kwargs)
        list_items = [
            ["name", r['title']],
            ['state', r['state']],
            ["subtype", r['subtype']],
            ["mimetype", r['mime_type']],
            ['detail-urk', r['detail_url']],
            ["download-url", r['href']]
        ]
        if kwargs['json']:
            import pprint
            pprint.pprint(r)
        else:
            show_list(values=list_items, headers=["key", "value"])

    def upload(self,
               **kwargs):

        document_path: Path = kwargs['file_path']
        if not document_path.exists():
            raise FileNotFoundError

        params = {
            # layer permissions
            "permissions": '{ "users": {"AnonymousUser": ["view_resourcebase"]} , "groups":{}}',
            'title': kwargs['title'],
            'abstract': kwargs['abstract'] if 'abstract' in kwargs else '',
            'metadata_only': kwargs['metadata_only'],
        }

        files: List[GeonodeHTTPFile]
        content_length: int = os.path.getsize(document_path)
        mimetype: Optional[str] = mimetypes.guess_type(document_path)[0]
        if mimetype:
            files = [
                ('doc_file', (document_path.name, open(document_path, 'rb'), mimetype)),
            ]
        else:
            files = [
                ('doc_file', (document_path.name, open(document_path, 'rb'))),
            ]

        return self.http_post(endpoint="documents",
                              files=files,
                              params=params,
                              content_length=content_length
                              )['document']
