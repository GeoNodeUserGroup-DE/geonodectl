from src.geonodeobject import GeoNodeObject, GeonodeCmdOutListKey, GeonodeCmdOutDictKey


class GeonodeResources(GeoNodeObject):
    DEFAULT_LIST_KEYS = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="state"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]

    RESOURCE_TYPE = "resources"
