from src.geonodeobject import GeoNodeObject, GeonodeCmdOutListKey, GeonodeCmdOutDictKey


class GeonodeMaps(GeoNodeObject):
    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]

    RESOURCE_TYPE = "maps"
