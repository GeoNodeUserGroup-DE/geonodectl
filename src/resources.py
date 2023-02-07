
from src.geonodeobject import GeoNodeObject


class GeonodeResources(GeoNodeObject):

    DEFAULT_LIST_KEYS = [{'type': list, 'key': 'pk'},
                         {'type': list, 'key': 'title'},
                         {'type': dict, 'key': ['owner', 'username']},
                         {'type': list, 'key': 'resource_type'},
                         {'type': list, 'key': 'state'},
                         {'type': list, 'key': 'detail_url'}]

    RESOURCE_TYPE = "resources"
