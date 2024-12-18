from typing import List

from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey


class GeonodeUploadsHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "uploads"
    SINGULAR_RESOURCE_NAME = "upload"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="id"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="create_date"),
        GeonodeCmdOutListKey(key="state"),
        GeonodeCmdOutListKey(key="link"),
    ]
