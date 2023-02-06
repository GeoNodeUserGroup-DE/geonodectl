
import os
import mimetypes

from src.geonodeobject import GeoNodeObject
from src.cmdprint import show_list


class GeonodeDocuments(GeoNodeObject):

  DEFAULT_LIST_KEYS = [{'type': list, 'key': 'pk'},
                       {'type': list, 'key': 'title'},
                       {'type': dict, 'key': ['owner', 'username']},
                       {'type': list, 'key': 'date'},
                       {'type': list, 'key': 'resource_type'},
                       {'type': list, 'key': 'detail_url'}]

  RESOURCE_TYPE = "documents"

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
             *args,
             **kwargs):

    document_path = kwargs['file_path']
    if not document_path.exists():
      raise FileNotFoundError

    params = {
      "permissions": '{ "users": {"AnonymousUser": ["view_resourcebase"]} , "groups":{}}',  # layer permissions
      'title': kwargs['title'],
      'abstract': kwargs['abstract'] if 'abstract' in kwargs else '',
      'metadata_only': kwargs['metadata_only'],
    }

    content_length = os.path.getsize(document_path)
    files = [
      ('doc_file', (document_path.name, open(document_path, 'rb'), mimetypes.guess_type(document_path)[0])),
    ]

    return self.http_post(endpoint="documents",
                          files=files,
                          params=params,
                          content_length=content_length
                          )['document']
