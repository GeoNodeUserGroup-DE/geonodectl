from typing import List

from .geonodetypes import (
    GeonodeCmdOutListKey,
    GeonodeCmdOutObjectKey,
    GeonodeCmdOutDictKey,
)
from .geonodeobject import GeonodeObjectHandler


class GeonodeThesauriKeywordsRequestHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = "tkeywords"
    JSON_OBJECT_NAME = "tkeywords"
    SINGULAR_RESOURCE_NAME = "tkeywords"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="keyword"),  # this only works on ZALF GeoNode backend
        GeonodeCmdOutDictKey(key=["thesaurus", "slug"]),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="slug"),
        GeonodeCmdOutListKey(key="uri"),
    ]
