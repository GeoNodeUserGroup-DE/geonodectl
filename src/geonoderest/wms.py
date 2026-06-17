from typing import Optional, Tuple
import logging

import requests

from geonoderest.rest import GeonodeRest


class GeonodeWmsHandler(GeonodeRest):
    """WMS GetMap proxied through the GeoNode-managed GeoServer.

    GeoServer is exposed at ``<geonode-base>/geoserver/ows`` (where
    ``<geonode-base>`` is the GeoNode URL without the ``/api/v2/`` suffix).

    GeoServer maintains its own user realm separate from Django's, so Basic
    Auth headers intended for the Django REST API are rejected by GeoServer.
    Authentication is performed via an OAuth2 ``access_token`` query
    parameter — the same token returned by ``/api/v2/userinfo``. This
    handler therefore issues anonymous HTTP and relies on the token in the
    URL for credentials.
    """

    def get_map(
        self,
        layer: str,
        bbox: Tuple[float, float, float, float],
        width: int = 512,
        height: int = 512,
        srs: str = "EPSG:3857",
        image_format: str = "image/png",
        styles: Optional[str] = None,
        transparent: bool = True,
        tiled: bool = True,
        access_token: Optional[str] = None,
        version: str = "1.3.0",
    ) -> requests.Response:
        """Issue a WMS GetMap request and return the raw response.

        Args:
            layer (str): Layer name (typically the ``alternate`` of a dataset).
            bbox (Tuple[float, float, float, float]): Bounding box in the
                requested SRS, ``(minx, miny, maxx, maxy)``.
            width (int): Image width in pixels. Defaults to 512.
            height (int): Image height in pixels. Defaults to 512.
            srs (str): Spatial reference system. Defaults to ``EPSG:3857``.
            image_format (str): MIME type. Defaults to ``image/png``.
            styles (Optional[str]): Style name. Defaults to the layer name
                (matching GeoNode's default-style convention).
            transparent (bool): Render with a transparent background.
                Defaults to True.
            tiled (bool): Pass through the GeoServer tiling hint.
                Defaults to True.
            access_token (Optional[str]): OAuth2 token granting GeoServer
                access. If omitted, the request is anonymous.
            version (str): WMS protocol version. Defaults to ``1.3.0``.

        Returns:
            requests.Response: The raw response. Image bytes are in
            ``response.content``; check ``response.ok`` and
            ``response.headers["Content-Type"]`` before consuming.
        """
        params = [
            ("SERVICE", "WMS"),
            ("VERSION", version),
            ("REQUEST", "GetMap"),
            ("FORMAT", image_format),
            ("TRANSPARENT", str(transparent).lower()),
            ("LAYERS", layer),
            ("STYLES", styles if styles is not None else layer),
            ("SRS", srs),
            ("CRS", srs),
            ("WIDTH", str(width)),
            ("HEIGHT", str(height)),
            ("BBOX", ",".join(str(c) for c in bbox)),
            ("TILED", str(tiled).lower()),
        ]
        if access_token:
            params.append(("access_token", access_token))

        url = f"{self.gn_credentials.get_geonode_base_url()}/geoserver/ows"
        logging.debug(f"WMS GET URL: {url}, params: {params}")
        return requests.get(url, params=params, verify=self.verify)
