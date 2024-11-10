from typing import List

from .geonodetypes import (
    GeonodeCmdOutListKey,
    GeonodeCmdOutObjectKey,
)
from .geonodeobject import GeonodeObjectHandler


class GeonodeKeywordsRequestHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = "keywords"
    JSON_OBJECT_NAME = "keywords"
    SINGULAR_RESOURCE_NAME = "keywords"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="id"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="slug"),
        GeonodeCmdOutListKey(key="link"),
    ]
