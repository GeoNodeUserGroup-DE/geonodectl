from typing import Dict, List, Optional

from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey
from geonoderest.geonodeobject import GeonodeObjectHandler


class GeonodeThesauriKeywordLabelsRequestHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = "tkeywordlabels"
    JSON_OBJECT_NAME = "ThesaurusKeywordLabels"
    SINGULAR_RESOURCE_NAME = "ThesaurusKeywordLabels"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="keyword"),  # this only works on ZALF GeoNode backend
        GeonodeCmdOutListKey(key="lang"),
        GeonodeCmdOutListKey(key="label"),
    ]

    def get(self, pk: int, **kwargs) -> Optional[Dict]:
        """
        get details for a given keyword (identifier)

        Args:
            pk (int): keyword of the object

        Returns:
            Dict: obj details
        """
        r = self.http_get(endpoint=f"{self.ENDPOINT_NAME}?keyword={pk}")
        if r is None:
            return None
        return r[self.SINGULAR_RESOURCE_NAME]
