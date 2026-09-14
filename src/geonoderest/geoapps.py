from geonoderest.resources import GeonodeResourceHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey


class GeonodeGeoappsHandler(GeonodeResourceHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "geoapps"
    SINGULAR_RESOURCE_NAME = "geoapp"
    # GeoNode reports a geoapp's own subtype (geostory, dashboard, ...) rather
    # than "geoapp", so resource_type_matches() matches these by exclusion
    UUID_RESOURCE_TYPE = "geoapp"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]
