"""Load JSON for the command line from a file, an http(s) URL or an inline string.

Every ``--json_path`` used to be read with a hand rolled ``open()`` + ``json.load()``
at each call site, none of which reported a missing or unreadable file properly.
:func:`load_json_source` is the single entry point all of them use now, and it takes
an http(s) URL wherever it takes a path - one argument, either kind of source.

Nothing in here talks to GeoNode or exits the process - handlers catch
:class:`JsonSourceError` and report it on the command line.
"""

import json
import logging
from typing import Any, Optional
from urllib.parse import urlsplit

import requests

# remote JSON is a small config file, not a download - fail fast instead of
# hanging a patch run on an unresponsive host
DEFAULT_TIMEOUT = 30


class JsonSourceError(Exception):
    """Raised when the JSON could not be obtained or is not valid JSON."""


def is_http_url(value: str) -> bool:
    """True when ``value`` is an http(s) URL rather than a local path."""
    return urlsplit(value).scheme in ("http", "https")


def fetch_json_url(url: str, timeout: int = DEFAULT_TIMEOUT, what: str = "json") -> Any:
    """Download and parse JSON from an http(s) URL.

    The request is deliberately anonymous: the GeoNode credentials held by
    ``GeonodeApiConf`` are never attached, as the URL routinely points at a host
    that has nothing to do with the GeoNode instance being managed.

    Args:
        url (str): http(s) URL to fetch
        timeout (int): seconds to wait for connect and for the response
        what (str): what is being read, used in the error messages

    Raises:
        JsonSourceError: the host is unreachable, answered with an error status
            or did not return valid JSON
    """
    logging.debug(f"fetching {what} from url: {url}")
    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise JsonSourceError(f"timeout after {timeout}s fetching {what} from {url}")
    except requests.exceptions.RequestException as e:
        # covers HTTPError from raise_for_status as well as connection failures
        raise JsonSourceError(f"could not fetch {what} from {url}: {e}")

    try:
        return r.json()
    except ValueError as e:
        # a login page or an error page served with 200 must not pass as json
        raise JsonSourceError(f"{url} did not return valid JSON: {e}")


def load_json_file(json_path: str, what: str = "json") -> Any:
    """Read and parse a JSON file from disk.

    Args:
        json_path (str): path to the json file
        what (str): what is being read, used in the error messages

    Raises:
        JsonSourceError: file missing, unreadable or not valid JSON
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise JsonSourceError(f"{what} file not found: {json_path}")
    except IsADirectoryError:
        raise JsonSourceError(f"{what} path is a directory: {json_path}")
    except PermissionError:
        raise JsonSourceError(f"{what} file not readable: {json_path}")
    except UnicodeDecodeError:
        raise JsonSourceError(f"{what} file is not UTF-8 encoded: {json_path}")
    except json.decoder.JSONDecodeError as e:
        raise JsonSourceError(f"{what} file is not valid JSON: {json_path}: {e}")


def load_json(source: str, timeout: int = DEFAULT_TIMEOUT, what: str = "json") -> Any:
    """Read JSON from ``source``, which is either a path or an http(s) URL.

    Args:
        source (str): path to a json file, or a http(s) url serving one
        timeout (int): request timeout, only used when ``source`` is a url
        what (str): what is being read, used in the error messages

    Raises:
        JsonSourceError: the source could not be read or is not valid JSON
    """
    if is_http_url(source):
        return fetch_json_url(source, timeout=timeout, what=what)
    return load_json_file(source, what=what)


def load_json_string(fields: str) -> Any:
    """Parse an inline JSON string as passed to ``--set``.

    Raises:
        JsonSourceError: the string is not valid JSON
    """
    try:
        return json.loads(fields)
    except json.decoder.JSONDecodeError as e:
        raise JsonSourceError(f"not a valid JSON string: {fields}: {e}")


def load_json_source(
    json_path: Optional[str] = None,
    fields: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    """Return the JSON given by whichever of the two sources was provided.

    The two are mutually exclusive on the command line, so at most one is ever
    set; the order below only decides what happens if a caller passes both.

    Args:
        json_path (Optional[str]): path to a json file, or a http(s) url serving one
        fields (Optional[str]): inline json string
        timeout (int): request timeout, only used when ``json_path`` is a url

    Raises:
        JsonSourceError: nothing was provided, or the source could not be read
    """
    if json_path:
        return load_json(json_path, timeout=timeout)
    if fields:
        return load_json_string(fields)
    raise JsonSourceError("At least one of 'fields' or 'json_path' must be provided.")
