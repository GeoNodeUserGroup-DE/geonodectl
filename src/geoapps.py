from src.resources import GeonodeResourceHandler
from src.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey


class GeonodeGeoappsHandler(GeonodeResourceHandler):
    RESOURCE_TYPE = "geoapps"
    SINGULAR_RESOURCE_NAME = "geoapp"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]
