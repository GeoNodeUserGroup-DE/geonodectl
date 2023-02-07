
from src.geonodeobject import GeoNodeObject


class GeonodeMaps(GeoNodeObject):
    DEFAULT_LIST_KEYS = [{'type': list, 'key': 'pk'},
                         {'type': list, 'key': 'title'},
                         {'type': dict, 'key': ['owner', 'username']},
                         {'type': list, 'key': 'resource_type'},
                         {'type': list, 'key': 'detail_url'}]

    RESOURCE_TYPE = "maps"
