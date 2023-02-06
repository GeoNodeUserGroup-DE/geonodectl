
from src.geonodeobject import GeoNodeObject


class GeonodePeople(GeoNodeObject):

  DEFAULT_LIST_KEYS = [{'type': list, 'key': 'pk'},
                       {'type': list, 'key': 'username'},
                       {'type': list, 'key': 'first_name'},
                       {'type': list, 'key': 'last_name'}]
  
  RESOURCE_TYPE = "users"