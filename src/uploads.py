from src.geonodeobject import (
    GeoNodeObject,
    GeonodeCmdOutListKey,
    GeonodeCmdOutObjectKey,
)
from typing import List


class GeonodeUploads(GeoNodeObject):
    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="id"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="create_date"),
        GeonodeCmdOutListKey(key="state"),
        GeonodeCmdOutListKey(key="link"),
    ]

    RESOURCE_TYPE = "uploads"
