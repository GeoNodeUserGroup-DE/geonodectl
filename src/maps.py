from src.resources import GeonodeResourceHandler
from src.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey


class GeonodeMapsHandler(GeonodeResourceHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "maps"
    SINGULAR_RESOURCE_NAME = "map"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]
