import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

import requests
import urllib3
from geo.Geoserver import Geoserver, GeoserverException

from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE

urllib3.disable_warnings()

SLD_CONTENT_TYPE = "application/vnd.ogc.sld+xml"

GEOSERVER_URL_ENV_VAR = "GEOSERVER_URL"
GEOSERVER_BASIC_AUTH_ENV_VAR = "GEOSERVER_API_BASIC_AUTH"
GEOSERVER_USER_ENV_VAR = "GEOSERVER_USER"
GEOSERVER_PASSWORD_ENV_VAR = "GEOSERVER_PASSWORD"

GEONODE_API_URL_ENV_VAR = "GEONODE_API_URL"


def _geonode_base_url(geonode_api_url: str) -> str:
    """Strip the ``/api/v2`` suffix from a GeoNode API URL."""
    url = geonode_api_url.rstrip("/")
    if url.endswith("/api/v2"):
        url = url[: -len("/api/v2")]
    return url.rstrip("/")


def _exc_msg(e: GeoserverException) -> str:
    msg = e.message
    if isinstance(msg, bytes):
        msg = msg.decode("utf-8", errors="replace")
    return f"HTTP {e.status}: {msg}"


class GeonodeGeoServerStyleHandler:
    """GeoServer REST API client for style management.

    Authentication (in order of precedence):
      GEOSERVER_API_BASIC_AUTH — Base64-encoded ``user:password`` (same format
                                  as GEONODE_API_BASIC_AUTH). Preferred.
      GEOSERVER_USER + GEOSERVER_PASSWORD — explicit credentials fallback.

    URL:
      GEOSERVER_URL — GeoServer base URL (default: GEONODE_API_URL with
                      ``/api/v2/`` replaced by ``/geoserver``).

    GeoNode proxy:
      GEONODE_API_URL — when set, ``set-default`` is sent through GeoNode's
                        ``/gs/rest/layers`` proxy so GeoNode syncs the new
                        default style into its own database.

    SSL verification follows GEONODE_API_VERIFY (True/False, default True).

    CLI subcommand routing:
      geoserver styles  <list|describe|upload|set-default>  → cmd_style_*
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        verify: bool = True,
        geonode_url: Optional[str] = None,
    ):
        self.base_url = url.rstrip("/")
        self.geonode_url = geonode_url.rstrip("/") if geonode_url else None
        self._auth = (username, password)
        self._verify = verify
        self.geo = Geoserver(
            service_url=self.base_url,
            username=username,
            password=password,
            request_options={"verify": verify},
        )

    @staticmethod
    def from_env() -> "GeonodeGeoServerStyleHandler":
        # --- URL: explicit or derived from GeoNode API URL ---
        geonode_api_url = os.getenv(GEONODE_API_URL_ENV_VAR, "")
        geonode_url = _geonode_base_url(geonode_api_url) if geonode_api_url else None
        url = os.getenv(GEOSERVER_URL_ENV_VAR)
        if not url:
            if not geonode_url:
                raise KeyError(
                    f"Set {GEOSERVER_URL_ENV_VAR} or {GEONODE_API_URL_ENV_VAR}"
                )
            url = geonode_url + "/geoserver"

        # --- Auth: GEOSERVER_API_BASIC_AUTH takes precedence ---
        basic_auth = os.getenv(GEOSERVER_BASIC_AUTH_ENV_VAR)
        if basic_auth:
            try:
                decoded = base64.b64decode(basic_auth).decode("utf-8")
                user, password = decoded.split(":", 1)
            except Exception as exc:
                raise ValueError(
                    f"Cannot decode {GEOSERVER_BASIC_AUTH_ENV_VAR}: {exc}"
                ) from exc
        else:
            user = os.environ[GEOSERVER_USER_ENV_VAR]
            password = os.environ[GEOSERVER_PASSWORD_ENV_VAR]

        verify = os.getenv("GEONODE_API_VERIFY", "True") == "True"
        return GeonodeGeoServerStyleHandler(
            url=url,
            username=user,
            password=password,
            verify=verify,
            geonode_url=geonode_url,
        )

    # ------------------------------------------------------------------
    # Style management  (geoserver styles …)
    # ------------------------------------------------------------------

    def cmd_style_list(self, workspace: Optional[str] = None, **kwargs) -> int:
        """List styles in GeoServer, optionally filtered to a workspace."""
        try:
            data = self.geo.get_styles(workspace=workspace)
        except GeoserverException as e:
            logging.error(f"Failed to list styles: {_exc_msg(e)}")
            return EXIT_FAILED
        styles = data.get("styles", {}).get("style", [])
        if isinstance(styles, dict):
            styles = [styles]
        for s in styles:
            print(s.get("name", ""))
        return EXIT_OK

    def cmd_style_describe(
        self, name: str, workspace: Optional[str] = None, **kwargs
    ) -> int:
        """Print the SLD XML for a named style.

        geoserver-rest only exposes JSON metadata via get_style(); the raw SLD
        body requires a direct request with the appropriate Accept header.
        """
        if workspace:
            url = f"{self.base_url}/rest/workspaces/{workspace}/styles/{name}.sld"
        else:
            url = f"{self.base_url}/rest/styles/{name}.sld"
        try:
            r = requests.get(url, auth=self._auth, verify=self._verify, timeout=15)
            r.raise_for_status()
            print(r.text)
        except requests.RequestException as e:
            logging.error(f"Failed to fetch SLD for '{name}': {e}")
            return EXIT_FAILED
        return EXIT_OK

    def cmd_style_upload(
        self,
        name: str,
        sld_path: str,
        workspace: str = "geonode",
        **kwargs,
    ) -> int:
        """Create or update a style from an SLD file.

        Args:
            name (str): style name in GeoServer
            sld_path (str): path to the SLD XML file
            workspace (str): target workspace (default: geonode)

        Returns:
            int: EXIT_OK, EXIT_FAILED when GeoServer rejected the style, or
                EXIT_USAGE when the SLD file cannot be read
        """
        try:
            sld_content = Path(sld_path).read_text(encoding="utf-8")
        except OSError as e:
            logging.error(f"could not read SLD file {sld_path}: {e}")
            return EXIT_USAGE

        try:
            self.geo.upload_style(path=sld_content, name=name, workspace=workspace)
        except GeoserverException as e:
            # Style already exists → upload_style raises on the POST step;
            # fall back to a direct PUT to update the existing SLD body.
            logging.warning(
                f"upload_style failed ({_exc_msg(e)}) — "
                f"attempting direct PUT to update existing style '{name}'"
            )
            url = f"{self.base_url}/rest/workspaces/{workspace}/styles/{name}"
            try:
                r = requests.put(
                    url,
                    data=sld_content.encode("utf-8"),
                    headers={"Content-Type": SLD_CONTENT_TYPE},
                    auth=self._auth,
                    verify=self._verify,
                    timeout=30,
                )
                r.raise_for_status()
            except requests.RequestException as put_err:
                logging.error(
                    f"Failed to upload SLD body for style '{name}': {put_err}"
                )
                return EXIT_FAILED

        print(json.dumps({"success": True, "style": name, "workspace": workspace}))
        return EXIT_OK

    def cmd_style_set_default(
        self,
        layer: str,
        style_name: str,
        workspace: str = "geonode",
        **kwargs,
    ) -> int:
        """Set the default style for a GeoServer layer.

        When the GeoNode URL is known, the request is sent through GeoNode's
        ``/gs/rest/layers`` proxy. GeoNode then syncs the new default style
        into its own database; a direct GeoServer call only updates GeoServer.

        Args:
            layer (str): fully qualified layer name, e.g. geonode:my_layer
            style_name (str): name of the style to set as default
            workspace (str): workspace of the style (default: geonode)

        Example:
          geonodectl geoserver styles set-default --layer geonode:my_layer --style my_style
        """
        # layer may arrive as "workspace:name" or bare "name"
        parts = layer.rsplit(":", 1)
        layer_workspace = parts[0] if len(parts) > 1 else workspace
        layer_name = parts[-1]

        if self.geonode_url:
            # GeoNode resolves the dataset by the bare layer name in the URL
            url = f"{self.geonode_url}/gs/rest/layers/{layer_name}.json"
            body = {
                "layer": {"defaultStyle": {"name": style_name, "workspace": workspace}}
            }
            try:
                r = requests.put(
                    url,
                    json=body,
                    auth=self._auth,
                    verify=self._verify,
                    timeout=30,
                )
                r.raise_for_status()
            except requests.RequestException as e:
                logging.error(f"Failed to set default style for layer '{layer}': {e}")
                return EXIT_FAILED
        else:
            logging.warning(
                f"{GEONODE_API_URL_ENV_VAR} not set — setting the style directly in "
                "GeoServer; GeoNode will not reflect the change until it is synced"
            )
            try:
                self.geo.publish_style(
                    layer_name=layer_name,
                    style_name=style_name,
                    workspace=layer_workspace,
                )
            except GeoserverException as e:
                logging.error(
                    f"Failed to set default style for layer '{layer}': {_exc_msg(e)}"
                )
                return EXIT_FAILED

        print(json.dumps({"success": True, "layer": layer, "style": style_name}))
        return EXIT_OK
