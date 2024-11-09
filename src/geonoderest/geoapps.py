from geonoderest.resources import GeonodeResourceHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey


class GeonodeGeoappsHandler(GeonodeResourceHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "geoapps"
    SINGULAR_RESOURCE_NAME = "geoapp"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]
