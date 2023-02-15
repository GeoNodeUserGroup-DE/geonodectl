from typing import List

from src.geonodeobject import GeonodeObjectHandler
from src.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey


class GeonodeUploadsHandler(GeonodeObjectHandler):
    RESOURCE_TYPE = "uploads"
    SINGULAR_RESOURCE_NAME = "upload"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="id"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="create_date"),
        GeonodeCmdOutListKey(key="state"),
        GeonodeCmdOutListKey(key="link"),
    ]
