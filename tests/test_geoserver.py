"""Tests for GeonodeGeoServerStyleHandler — style management."""

import base64
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests
from geo.Geoserver import GeoserverException

from geonoderest.geoserver import GeonodeGeoServerStyleHandler

WORKSPACE = "geonode"
STYLE_NAME = "foss4g_buildings"
SLD = "<StyledLayerDescriptor/>"


def _handler() -> GeonodeGeoServerStyleHandler:
    with patch("geonoderest.geoserver.Geoserver"):
        h = GeonodeGeoServerStyleHandler(
            url="https://geoserver.example.com",
            username="admin",
            password="secret",
            verify=False,
        )
    h.geo = MagicMock()
    return h


# ------------------------------------------------------------------
# Style management tests
# ------------------------------------------------------------------


class TestCmdStyleList(unittest.TestCase):
    def setUp(self):
        self.h = _handler()

    def test_prints_style_names(self, *_):
        self.h.geo.get_styles.return_value = {
            "styles": {
                "style": [
                    {"name": "foss4g_buildings"},
                    {"name": "foss4g_pois"},
                ]
            }
        }
        with patch("builtins.print") as mock_print:
            self.h.cmd_style_list(workspace=WORKSPACE)
        names = [c.args[0] for c in mock_print.call_args_list]
        self.assertIn("foss4g_buildings", names)
        self.assertIn("foss4g_pois", names)

    def test_wraps_single_style_dict(self):
        self.h.geo.get_styles.return_value = {
            "styles": {"style": {"name": "only_style"}}
        }
        with patch("builtins.print") as mock_print:
            self.h.cmd_style_list()
        self.assertEqual(mock_print.call_args.args[0], "only_style")

    def test_logs_error_on_geoserver_exception(self):
        self.h.geo.get_styles.side_effect = GeoserverException(500, b"error")
        with self.assertLogs(level="ERROR"):
            self.h.cmd_style_list(workspace=WORKSPACE)


class TestCmdStyleDescribe(unittest.TestCase):
    def setUp(self):
        self.h = _handler()

    @patch("geonoderest.geoserver.requests.get")
    def test_prints_sld_content(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, text=SLD, raise_for_status=lambda: None
        )
        with patch("builtins.print") as mock_print:
            self.h.cmd_style_describe(STYLE_NAME, workspace=WORKSPACE)
        mock_print.assert_called_once_with(SLD)

    @patch("geonoderest.geoserver.requests.get")
    def test_uses_workspace_url_when_provided(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200, text=SLD, raise_for_status=lambda: None
        )
        self.h.cmd_style_describe(STYLE_NAME, workspace=WORKSPACE)
        url = mock_get.call_args.args[0]
        self.assertIn(f"workspaces/{WORKSPACE}/styles", url)

    @patch("geonoderest.geoserver.requests.get")
    def test_logs_error_on_http_failure(self, mock_get):
        mock_get.side_effect = requests.RequestException("404")
        with self.assertLogs(level="ERROR"):
            self.h.cmd_style_describe(STYLE_NAME, workspace=WORKSPACE)


class TestCmdStyleUpload(unittest.TestCase):
    def setUp(self):
        self.h = _handler()
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sld", delete=False, mode="w")
        self.tmp.write(SLD)
        self.tmp.close()
        self.sld_path = self.tmp.name

    def tearDown(self):
        os.unlink(self.sld_path)

    def test_delegates_to_upload_style(self):
        self.h.geo.upload_style.return_value = 200
        with patch("builtins.print"):
            self.h.cmd_style_upload(STYLE_NAME, self.sld_path, workspace=WORKSPACE)
        self.h.geo.upload_style.assert_called_once_with(
            path=SLD, name=STYLE_NAME, workspace=WORKSPACE
        )

    def test_prints_success_json(self):
        self.h.geo.upload_style.return_value = 200
        with patch("builtins.print") as mock_print:
            self.h.cmd_style_upload(STYLE_NAME, self.sld_path, workspace=WORKSPACE)
        printed = json.loads(mock_print.call_args.args[0])
        self.assertTrue(printed["success"])
        self.assertEqual(printed["style"], STYLE_NAME)

    @patch("geonoderest.geoserver.requests.put")
    def test_falls_back_to_direct_put_when_upload_style_raises(self, mock_put):
        """Regression: if upload_style fails (style already exists), must still
        attempt a direct PUT to update the existing SLD body."""
        self.h.geo.upload_style.side_effect = GeoserverException(409, b"Already exists")
        mock_put.return_value = MagicMock(
            status_code=200, raise_for_status=lambda: None
        )
        with patch("builtins.print"):
            self.h.cmd_style_upload(STYLE_NAME, self.sld_path, workspace=WORKSPACE)
        mock_put.assert_called_once()
        _, kwargs = mock_put.call_args
        self.assertIn("application/vnd.ogc.sld+xml", kwargs["headers"]["Content-Type"])

    @patch("geonoderest.geoserver.requests.put")
    def test_logs_error_when_both_upload_and_put_fail(self, mock_put):
        self.h.geo.upload_style.side_effect = GeoserverException(500, b"error")
        mock_put.side_effect = requests.RequestException("refused")
        with self.assertLogs(level="ERROR"):
            self.h.cmd_style_upload(STYLE_NAME, self.sld_path, workspace=WORKSPACE)


class TestCmdStyleSetDefault(unittest.TestCase):
    def setUp(self):
        self.h = _handler()

    def test_splits_qualified_layer_for_publish_style(self):
        self.h.geo.publish_style.return_value = 200
        with patch("builtins.print"):
            self.h.cmd_style_set_default("geonode:buildings", STYLE_NAME)
        self.h.geo.publish_style.assert_called_once_with(
            layer_name="buildings",
            style_name=STYLE_NAME,
            workspace="geonode",
        )

    def test_uses_workspace_arg_for_bare_layer_name(self):
        self.h.geo.publish_style.return_value = 200
        with patch("builtins.print"):
            self.h.cmd_style_set_default("buildings", STYLE_NAME, workspace="custom")
        self.h.geo.publish_style.assert_called_once_with(
            layer_name="buildings",
            style_name=STYLE_NAME,
            workspace="custom",
        )

    def test_prints_success_json(self):
        self.h.geo.publish_style.return_value = 200
        with patch("builtins.print") as mock_print:
            self.h.cmd_style_set_default("geonode:buildings", STYLE_NAME)
        printed = json.loads(mock_print.call_args.args[0])
        self.assertTrue(printed["success"])
        self.assertEqual(printed["layer"], "geonode:buildings")
        self.assertEqual(printed["style"], STYLE_NAME)

    def test_logs_error_on_geoserver_exception(self):
        self.h.geo.publish_style.side_effect = GeoserverException(
            404, b"layer not found"
        )
        with self.assertLogs(level="ERROR"):
            self.h.cmd_style_set_default("geonode:buildings", STYLE_NAME)


class TestFromEnv(unittest.TestCase):
    """from_env: auth priority and URL defaulting."""

    def _make(self, env: dict):
        with (
            patch.dict(os.environ, env, clear=True),
            patch("geonoderest.geoserver.Geoserver") as mock_gs,
        ):
            h = GeonodeGeoServerStyleHandler.from_env()
            return h, mock_gs

    def test_basic_auth_var_decodes_credentials(self):
        token = base64.b64encode(b"admin:s3cr3t").decode()
        h, mock_gs = self._make(
            {
                "GEOSERVER_API_BASIC_AUTH": token,
                "GEOSERVER_URL": "https://gs.example.com",
            }
        )
        _, kwargs = mock_gs.call_args
        self.assertEqual(kwargs["username"], "admin")
        self.assertEqual(kwargs["password"], "s3cr3t")

    def test_user_password_vars_used_as_fallback(self):
        h, mock_gs = self._make(
            {
                "GEOSERVER_USER": "admin",
                "GEOSERVER_PASSWORD": "pw",
                "GEOSERVER_URL": "https://gs.example.com",
            }
        )
        _, kwargs = mock_gs.call_args
        self.assertEqual(kwargs["username"], "admin")
        self.assertEqual(kwargs["password"], "pw")

    def test_basic_auth_takes_precedence_over_user_password(self):
        token = base64.b64encode(b"tokenuser:tokenpass").decode()
        h, mock_gs = self._make(
            {
                "GEOSERVER_API_BASIC_AUTH": token,
                "GEOSERVER_USER": "other",
                "GEOSERVER_PASSWORD": "other",
                "GEOSERVER_URL": "https://gs.example.com",
            }
        )
        _, kwargs = mock_gs.call_args
        self.assertEqual(kwargs["username"], "tokenuser")

    def test_url_defaults_from_geonode_api_url(self):
        token = base64.b64encode(b"admin:pw").decode()
        h, mock_gs = self._make(
            {
                "GEOSERVER_API_BASIC_AUTH": token,
                "GEONODE_API_URL": "https://geonode.example.com/api/v2/",
            }
        )
        _, kwargs = mock_gs.call_args
        self.assertEqual(kwargs["service_url"], "https://geonode.example.com/geoserver")

    def test_explicit_geoserver_url_overrides_default(self):
        token = base64.b64encode(b"admin:pw").decode()
        h, mock_gs = self._make(
            {
                "GEOSERVER_API_BASIC_AUTH": token,
                "GEOSERVER_URL": "https://custom.gs.example.com",
                "GEONODE_API_URL": "https://geonode.example.com/api/v2/",
            }
        )
        _, kwargs = mock_gs.call_args
        self.assertEqual(kwargs["service_url"], "https://custom.gs.example.com")

    def test_raises_when_neither_url_nor_geonode_url_set(self):
        token = base64.b64encode(b"admin:pw").decode()
        with self.assertRaises(KeyError):
            with (
                patch.dict(
                    os.environ,
                    {"GEOSERVER_API_BASIC_AUTH": token},
                    clear=True,
                ),
                patch("geonoderest.geoserver.Geoserver"),
            ):
                GeonodeGeoServerStyleHandler.from_env()

    def test_raises_on_invalid_basic_auth_encoding(self):
        with self.assertRaises(ValueError):
            with (
                patch.dict(
                    os.environ,
                    {
                        "GEOSERVER_API_BASIC_AUTH": "!!!not-base64!!!",
                        "GEOSERVER_URL": "https://gs.example.com",
                    },
                    clear=True,
                ),
                patch("geonoderest.geoserver.Geoserver"),
            ):
                GeonodeGeoServerStyleHandler.from_env()


if __name__ == "__main__":
    unittest.main()
