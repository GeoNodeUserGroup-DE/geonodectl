import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.documents import GeonodeDocumentsHandler
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK

API_ALLOWS_POST = {"GET", "PATCH", "POST"}
API_FORBIDS_POST = {"GET", "PATCH"}

# what the documents api answers a successful POST with
API_UPLOAD_RESPONSE = {"document": {"pk": 42, "title": "report.pdf"}}
# what documents/upload?no__redirect=true answers a successful POST with
FORM_UPLOAD_RESPONSE = {"success": True, "url": "/catalogue/#/document/42"}

ENV = GeonodeApiConf(
    url="https://example.org/api/v2/", auth_basic="dXNlcjpwYXNz", verify=True
)


class DocumentFileTestCase(unittest.TestCase):
    """base for the upload tests, which need a file that really is there"""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.document = Path(self.tempdir.name) / "report.pdf"
        self.document.write_bytes(b"%PDF-1.4 not really a pdf")
        self.addCleanup(self.tempdir.cleanup)


class TestGeonodeDocumentsHandler(unittest.TestCase):
    @patch.object(GeonodeDocumentsHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {
            "document": [{"pk": 123, "title": "Test Document"}]
        }
        handler = GeonodeDocumentsHandler(env={})
        result = handler.get(123)
        self.assertEqual(result[0]["title"], "Test Document")

    @patch.object(GeonodeDocumentsHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeDocumentsHandler(env={})
        result = handler.patch(123, json_content={"title": "Updated"})
        self.assertTrue(result["success"])

    @patch.object(GeonodeDocumentsHandler, "http_delete")
    def test_delete_uses_resources_endpoint(self, mock_http_delete):
        """documents API does not allow DELETE — delete must use resources/{pk}/delete."""
        mock_http_delete.return_value = {}
        handler = GeonodeDocumentsHandler(env={})
        handler.delete(pk=7)
        mock_http_delete.assert_called_once_with(endpoint="resources/7/delete")


class TestDocumentUploadEndpointChoice(DocumentFileTestCase):
    """which endpoint creates the document, see #175"""

    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_post")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_api_endpoint_when_post_is_allowed(
        self, mock_allowed, mock_post, mock_form
    ):
        mock_allowed.return_value = API_ALLOWS_POST
        mock_post.return_value = API_UPLOAD_RESPONSE

        handler = GeonodeDocumentsHandler(env={})
        result = handler.upload(file_path=self.document)

        mock_allowed.assert_called_once_with("documents")
        mock_form.assert_not_called()
        self.assertEqual(mock_post.call_args.kwargs["endpoint"], "documents")
        self.assertEqual(result, API_UPLOAD_RESPONSE["document"])

    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_post")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_api_endpoint_when_probe_is_inconclusive(
        self, mock_allowed, mock_post, mock_form
    ):
        """no Allow header means unknown, not 'nothing is allowed'"""
        mock_allowed.return_value = None
        mock_post.return_value = API_UPLOAD_RESPONSE

        GeonodeDocumentsHandler(env={}).upload(file_path=self.document)

        mock_form.assert_not_called()
        mock_post.assert_called_once()

    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "http_post")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_form_view_when_post_is_not_allowed(
        self, mock_allowed, mock_form, mock_post, mock_get
    ):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = FORM_UPLOAD_RESPONSE
        mock_get.return_value = {"pk": 42, "title": "report.pdf"}

        handler = GeonodeDocumentsHandler(env={})
        result = handler.upload(file_path=self.document)

        mock_post.assert_not_called()
        kwargs = mock_form.call_args.kwargs
        self.assertEqual(kwargs["path"], "documents/upload")
        self.assertEqual(kwargs["params"], {"no__redirect": "true"})
        # the detail url is all the view returns, so the document is fetched back
        mock_get.assert_called_once_with(pk=42)
        self.assertEqual(result, mock_get.return_value)


class TestDocumentUploadPayload(DocumentFileTestCase):
    @patch.object(GeonodeDocumentsHandler, "http_post")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_api_fields_travel_as_form_data(self, mock_allowed, mock_post):
        """requests drops a json body when files are given, so these must be data"""
        mock_allowed.return_value = API_ALLOWS_POST
        mock_post.return_value = API_UPLOAD_RESPONSE

        GeonodeDocumentsHandler(env={}).upload(
            file_path=self.document, metadata_only=True
        )

        kwargs = mock_post.call_args.kwargs
        self.assertNotIn("json", kwargs)
        self.assertEqual(kwargs["data"], {"title": "report.pdf", "metadata_only": True})
        self.assertEqual(kwargs["content_length"], os.path.getsize(self.document))
        field, (name, _handle, mimetype) = kwargs["files"][0]
        self.assertEqual(
            (field, name, mimetype), ("doc_file", "report.pdf", "application/pdf")
        )

    @patch.object(GeonodeDocumentsHandler, "http_post")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_title_defaults_to_the_file_name(self, mock_allowed, mock_post):
        mock_allowed.return_value = API_ALLOWS_POST
        mock_post.return_value = API_UPLOAD_RESPONSE

        GeonodeDocumentsHandler(env={}).upload(file_path=self.document)

        self.assertEqual(mock_post.call_args.kwargs["data"]["title"], "report.pdf")

    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_given_title_wins_on_the_form_view(self, mock_allowed, mock_form, mock_get):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = FORM_UPLOAD_RESPONSE
        mock_get.return_value = {"pk": 42}

        GeonodeDocumentsHandler(env={}).upload(
            file_path=self.document, title="A custom title"
        )

        self.assertEqual(
            mock_form.call_args.kwargs["data"], {"title": "A custom title"}
        )

    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "patch")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_metadata_only_is_patched_after_the_form_upload(
        self, mock_allowed, mock_form, mock_patch, mock_get
    ):
        """the upload form has no metadata_only field"""
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = FORM_UPLOAD_RESPONSE
        mock_patch.return_value = {"document": {"pk": 42}}
        mock_get.return_value = {"pk": 42}

        GeonodeDocumentsHandler(env={}).upload(
            file_path=self.document, metadata_only=True
        )

        mock_patch.assert_called_once_with(pk=42, json_content={"metadata_only": True})

    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "patch")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_metadata_only_reports_what_the_patch_returned(
        self, mock_allowed, mock_form, mock_patch, mock_get
    ):
        """geonode hides a metadata_only document from the documents endpoint,
        so it is read back before the patch and reported from the patch body"""
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = FORM_UPLOAD_RESPONSE
        mock_get.return_value = {"pk": 42, "metadata_only": False}
        mock_patch.return_value = {"document": {"pk": 42, "metadata_only": True}}

        result = GeonodeDocumentsHandler(env={}).upload(
            file_path=self.document, metadata_only=True
        )

        self.assertEqual(result, {"pk": 42, "metadata_only": True})

    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "patch")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_a_failed_metadata_only_patch_fails_the_upload(
        self, mock_allowed, mock_form, mock_patch, mock_get
    ):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = FORM_UPLOAD_RESPONSE
        mock_get.return_value = {"pk": 42}
        mock_patch.return_value = None

        handler = GeonodeDocumentsHandler(env={})
        with self.assertLogs(level="ERROR"):
            result = handler.upload(file_path=self.document, metadata_only=True)

        self.assertIsNone(result)

    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "patch")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_no_patch_without_metadata_only(
        self, mock_allowed, mock_form, mock_patch, mock_get
    ):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = FORM_UPLOAD_RESPONSE
        mock_get.return_value = {"pk": 42}

        GeonodeDocumentsHandler(env={}).upload(file_path=self.document)

        mock_patch.assert_not_called()


class TestDocumentUploadFailures(DocumentFileTestCase):
    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_unparsable_detail_url_fails(self, mock_allowed, mock_form, mock_get):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = {"success": True, "url": "/catalogue/#/document/"}

        handler = GeonodeDocumentsHandler(env={})
        with self.assertLogs(level="ERROR"):
            result = handler.upload(file_path=self.document)

        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_an_unreadable_path_costs_no_request(self, mock_allowed):
        """the file is opened before the endpoint is probed"""
        handler = GeonodeDocumentsHandler(env={})
        with self.assertRaises(OSError):
            handler.upload(file_path=Path(self.tempdir.name))

        mock_allowed.assert_not_called()

    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_rejected_upload_fails(self, mock_allowed, mock_form):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = {
            "success": False,
            "message": "This file type is not allowed",
        }

        handler = GeonodeDocumentsHandler(env={})
        with self.assertLogs(level="ERROR") as logs:
            result = handler.upload(file_path=self.document)

        self.assertIsNone(result)
        self.assertIn("This file type is not allowed", "\n".join(logs.output))

    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_cmd_upload_reports_a_failed_upload(self, mock_allowed, mock_form):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = None

        handler = GeonodeDocumentsHandler(env={})
        with self.assertLogs(level="ERROR"):
            code = handler.cmd_upload(file_path=self.document, json=False)

        self.assertEqual(code, EXIT_FAILED)

    @patch.object(GeonodeDocumentsHandler, "get")
    @patch.object(GeonodeDocumentsHandler, "http_post_form")
    @patch.object(GeonodeDocumentsHandler, "http_allowed_methods")
    def test_cmd_upload_passes_the_title_through(
        self, mock_allowed, mock_form, mock_get
    ):
        mock_allowed.return_value = API_FORBIDS_POST
        mock_form.return_value = FORM_UPLOAD_RESPONSE
        mock_get.return_value = {
            "title": "A custom title",
            "state": "PROCESSED",
            "subtype": "document",
            "mime_type": "application/pdf",
            "detail_url": "/catalogue/#/document/42",
            "href": "https://example.org/documents/42",
        }

        handler = GeonodeDocumentsHandler(env={})
        code = handler.cmd_upload(
            file_path=self.document, title="A custom title", json=False
        )

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(
            mock_form.call_args.kwargs["data"], {"title": "A custom title"}
        )


class TestHttpPostForm(unittest.TestCase):
    """the csrf dance the non-api form views need"""

    def test_bootstraps_csrf_and_posts(self):
        handler = GeonodeDocumentsHandler(env=ENV)
        with patch("geonoderest.rest.requests.Session") as session_cls:
            session = session_cls.return_value
            session.cookies.get.return_value = "a-csrf-token"
            response = session.post.return_value
            response.is_redirect = False
            response.json.return_value = {"success": True}

            result = handler.http_post_form(
                path="documents/upload",
                data={"title": "report.pdf"},
                params={"no__redirect": "true"},
            )

        # the cookie comes from the landing page, fetched before the post
        session.get.assert_called_once_with("https://example.org/")
        kwargs = session.post.call_args.kwargs
        self.assertEqual(
            session.post.call_args.args[0], "https://example.org/documents/upload"
        )
        self.assertEqual(kwargs["headers"]["X-CSRFToken"], "a-csrf-token")
        self.assertEqual(
            kwargs["headers"]["Referer"], "https://example.org/documents/upload"
        )
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(result, {"success": True})
        session.close.assert_called_once()

    def test_a_redirect_is_a_failure(self):
        """following it would silently turn the POST into a GET of the login page"""
        handler = GeonodeDocumentsHandler(env=ENV)
        with patch("geonoderest.rest.requests.Session") as session_cls:
            session = session_cls.return_value
            session.cookies.get.return_value = "a-csrf-token"
            response = session.post.return_value
            response.is_redirect = True
            response.headers = {"Location": "https://example.org/account/login/"}

            with self.assertLogs(level="ERROR") as logs:
                result = handler.http_post_form(path="documents/upload")

        self.assertIsNone(result)
        self.assertIn("account/login", "\n".join(logs.output))
        response.raise_for_status.assert_not_called()


if __name__ == "__main__":
    unittest.main()
