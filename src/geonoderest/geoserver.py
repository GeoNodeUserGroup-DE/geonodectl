import json
import logging
import os
from pathlib import Path
from typing import Optional

import requests
import urllib3
from geo.Geoserver import Geoserver, GeoserverException

urllib3.disable_warnings()

SLD_CONTENT_TYPE = "application/vnd.ogc.sld+xml"

GEOSERVER_URL_ENV_VAR = "GEOSERVER_URL"
GEOSERVER_USER_ENV_VAR = "GEOSERVER_USER"
GEOSERVER_PASSWORD_ENV_VAR = "GEOSERVER_PASSWORD"


def _exc_msg(e: GeoserverException) -> str:
    msg = e.message
    if isinstance(msg, bytes):
        msg = msg.decode("utf-8", errors="replace")
    return f"HTTP {e.status}: {msg}"


class GeonodeGeoServerHandler:
    """GeoServer REST API client for style management.

    Reads connection details from environment variables:
      GEOSERVER_URL      — base URL, e.g. https://geonode.example.com/geoserver
      GEOSERVER_USER     — GeoServer admin username
      GEOSERVER_PASSWORD — GeoServer admin password

    SSL verification follows GEONODE_API_VERIFY (True/False, default True).
    """

    def __init__(self, url: str, username: str, password: str, verify: bool = True):
        self.base_url = url.rstrip("/")
        self._auth = (username, password)
        self._verify = verify
        self.geo = Geoserver(
            service_url=self.base_url,
            username=username,
            password=password,
            request_options={"verify": verify},
        )

    @staticmethod
    def from_env() -> "GeonodeGeoServerHandler":
        url = os.environ[GEOSERVER_URL_ENV_VAR]
        user = os.environ[GEOSERVER_USER_ENV_VAR]
        password = os.environ[GEOSERVER_PASSWORD_ENV_VAR]
        verify = os.getenv("GEONODE_API_VERIFY", "True") == "True"
        return GeonodeGeoServerHandler(url=url, username=user, password=password, verify=verify)

    # ------------------------------------------------------------------
    # cmd_ methods (called by geonodectl dispatch)
    # ------------------------------------------------------------------

    def cmd_list(self, workspace: Optional[str] = None, **kwargs):
        """List styles in GeoServer, optionally filtered to a workspace."""
        try:
            data = self.geo.get_styles(workspace=workspace)
        except GeoserverException as e:
            logging.error(f"Failed to list styles: {_exc_msg(e)}")
            return
        styles = data.get("styles", {}).get("style", [])
        if isinstance(styles, dict):
            styles = [styles]
        for s in styles:
            print(s.get("name", ""))

    def cmd_describe(self, name: str, workspace: Optional[str] = None, **kwargs):
        """Print the SLD XML for a style.

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

    def cmd_upload(
        self,
        name: str,
        sld_path: str,
        workspace: str = "geonode",
        **kwargs,
    ):
        """Create or update a style from an SLD file.

        Args:
            name (str): style name in GeoServer
            sld_path (str): path to the SLD XML file
            workspace (str): target workspace (default: geonode)
        """
        sld_content = Path(sld_path).read_text(encoding="utf-8")

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
                logging.error(f"Failed to upload SLD body for style '{name}': {put_err}")
                return

        print(json.dumps({"success": True, "style": name, "workspace": workspace}))

    def cmd_set_default(
        self,
        layer: str,
        style_name: str,
        workspace: str = "geonode",
        **kwargs,
    ):
        """Set the default style for a GeoServer layer.

        Args:
            layer (str): fully qualified layer name, e.g. geonode:my_layer
            style_name (str): name of the style to set as default
            workspace (str): workspace of the layer (default: geonode)

        Example:
          geonodectl geoserver styles set-default geonode:my_layer my_style
        """
        # layer may arrive as "workspace:name" or bare "name"
        parts = layer.rsplit(":", 1)
        layer_workspace = parts[0] if len(parts) > 1 else workspace
        layer_name = parts[-1]

        try:
            self.geo.publish_style(
                layer_name=layer_name,
                style_name=style_name,
                workspace=layer_workspace,
            )
        except GeoserverException as e:
            logging.error(f"Failed to set default style for layer '{layer}': {_exc_msg(e)}")
            return

        print(json.dumps({"success": True, "layer": layer, "style": style_name}))
