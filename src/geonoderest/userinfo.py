from typing import Dict, Optional

from geonoderest.rest import GeonodeRest


class GeonodeUserInfoHandler(GeonodeRest):
    """GET /api/v2/userinfo — identity claims for the authenticated user.

    On GeoNode deployments that grant a session token, the response also
    includes an `access_token` usable to authenticate downstream services
    such as the bundled GeoServer.
    """

    ENDPOINT_NAME = "userinfo"

    def get(self, **kwargs) -> Optional[Dict]:
        """Return the userinfo claims dict, or None on error."""
        return self.http_get(endpoint=f"{self.ENDPOINT_NAME}/")
