from src.geonodeobject import GeoNodeObject, GeonodeCmdOutListKey


class GeonodePeople(GeoNodeObject):
    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="username"),
        GeonodeCmdOutListKey(key="first_name"),
        GeonodeCmdOutListKey(key="last_name"),
    ]

    RESOURCE_TYPE = "users"
