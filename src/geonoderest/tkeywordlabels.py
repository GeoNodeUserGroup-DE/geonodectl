from typing import Dict, List

from .geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey
from .geonodeobject import GeonodeObjectHandler


class GeonodeThesauriKeywordLabelsRequestHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = "tkeywordlabels"
    JSON_OBJECT_NAME = "ThesaurusKeywordLabels"
    SINGULAR_RESOURCE_NAME = "ThesaurusKeywordLabels"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="keyword"),  # this only works on ZALF GeoNode backend
        GeonodeCmdOutListKey(key="lang"),
        GeonodeCmdOutListKey(key="label"),
    ]

    def get(self, pk: int, **kwargs) -> Dict:
        """
        get details for a given keyword (identifier)

        Args:
            pk (int): keyword of the object

        Returns:
            Dict: obj details
        """
        r = self.http_get(endpoint=f"{self.ENDPOINT_NAME}?keyword={pk}")
        return r[self.SINGULAR_RESOURCE_NAME]
