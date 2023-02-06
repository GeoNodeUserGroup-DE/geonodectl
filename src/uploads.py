
from src.geonodeobject import GeoNodeObject

class GeonodeUploads(GeoNodeObject):

  DEFAULT_LIST_KEYS = [{'type': list, 'key': 'id'},
                       {'type': list, 'key': 'name'},
                       {'type': list, 'key': 'create_date'},
                       {'type': list, 'key': 'state'},
                       {'type': list, 'key': 'link'}]

  RESOURCE_TYPE = "uploads"