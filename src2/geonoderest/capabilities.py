from .cmdprint import print_list_on_cmd
from .geonodetypes import GeonodeCmdOutListKey
# --- Imports ---
# Standard library
import logging
import json
import sys
import os
from pathlib import Path

# Third-party
import requests

# Typing
from typing import Any, Dict, List, Optional, Union


class AttributeDescribeCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def get(self, pk: int, **kwargs: Any) -> Optional[Dict[str, Any]]:
        try:
            endpoint = f"datasets/{pk}/attribute_set"
            result = self.base.http_get(endpoint=endpoint)
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in attribute get: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in attribute get: {e}")
            return {"error": str(e)}

    def cmd_describe(self, pk: int, **kwargs: Any) -> Optional[Dict[str, Any]]:
        try:
            obj = self.get(pk, **kwargs)
            if not obj or not isinstance(obj, dict):
                return {"error": "No object returned"}
            if kwargs.get("json"):
                print(obj)
            else:
                attributes = [
                    [
                        attr.get("pk"),
                        attr.get("attribute"),
                        attr.get("attribute_label"),
                        attr.get("description"),
                        attr.get("attribute_type"),
                    ]
                    for attr in obj.get("attributes", [])
                    if isinstance(attr, dict)
                ]
                print(attributes)
            return {}
        except Exception as e:
            logging.error(f"Error in cmd_describe: {e}")
            return {"error": str(e)}


class AttributePatchCapable:
    def __init__(self, base: Any) -> None:
        self.base = base
        return None

    def cmd_patch(
        self,
        pk: int,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            json_content = None
            if json_path:
                with open(json_path, "r") as file:
                    try:
                        json_content = json.load(file)
                    except json.decoder.JSONDecodeError as E:
                        print(f"JSON decode error: {E}")
            elif fields:
                try:
                    json_content = json.loads(fields)
                except json.decoder.JSONDecodeError as E:
                    print(f"JSON decode error: {E}")
            else:
                raise ValueError(
                    "At least one of 'fields' or 'json_path' must be provided."
                )
            if json_content is None:
                raise ValueError("No JSON content provided ...")
            obj = self.patch(pk=pk, json_content=json_content, **kwargs)
            print(obj)
            return None
        except Exception as e:
            logging.error(f"Error in cmd_patch: {e}")
            return {"error": str(e)}

    def patch(
        self, pk: int, json_content: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        try:
            endpoint = f"datasets/{pk}/"
            attributes = None
            if json_content is not None and "attribute_set" in json_content:
                attributes = {"attribute": json_content.pop("attribute_set")}
            elif json_content is not None and "attribute" in json_content:
                attributes = {"attribute": json_content.pop("attribute")}
            result = self.base.http_patch(endpoint, data=attributes, **kwargs)
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in attribute patch: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in attribute patch: {e}")
            return {"error": str(e)}


# --- Linked Resource Capability ---
class LinkedResourceCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def cmd_add(
        self, pk: int, linked_to: Optional[List[Any]] = None, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        if linked_to is None:
            linked_to = []
        try:
            if len(linked_to) == 0:
                logging.warning(
                    "missing linked_to parameter for deletion, doing nothing ... "
                )
                import sys

                sys.exit(0)
            obj = self.add(pk=pk, linked_to=linked_to, **kwargs)
            if obj is None:
                logging.warning("add failed ... ")
            else:
                print(obj)
        except Exception as e:
            logging.error(f"Error in cmd_add: {e}")
            return {"error": str(e)}
        return None

    def add(
        self, pk: int, linked_to: Optional[List[Any]] = None, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        if linked_to is None:
            linked_to = []
        try:
            json_content = {"target": list(linked_to)}
            endpoint = f"resources/{pk}/linked_resources"
            result = self.base.http_post(endpoint=endpoint, json=json_content)
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in add: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in add: {e}")
            return {"error": str(e)}

    def cmd_delete(
        self, pk: int, linked_to: List[Any], **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        try:
            if len(linked_to) == 0:
                logging.warning(
                    "missing linked_to parameter for deletion, doing nothing ... "
                )
                import sys

                sys.exit(0)
            obj = self.delete(pk=pk, linked_to=linked_to, **kwargs)
            if obj is None:
                logging.warning("delete failed ... ")
            else:
                print(obj)
        except Exception as e:
            logging.error(f"Error in cmd_delete: {e}")
            return {"error": str(e)}
        return None

    def delete(
        self, pk: int, linked_to: Optional[List[Any]] = None, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        if linked_to is None:
            linked_to = []
        try:
            endpoint = f"resources/{pk}/linked_resources"
            json_content = {"target": list(linked_to)}
            result = self.base.http_delete(endpoint=endpoint, json=json_content)
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in delete: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in delete: {e}")
            return {"error": str(e)}

    def cmd_describe(self, pk: int, **kwargs: Any) -> Optional[Dict[str, Any]]:
        try:
            obj = self.get(pk, **kwargs)
            if kwargs.get("json"):
                print(obj)
            else:
                linked_to_values = []
                linked_by_values = []
                if obj and isinstance(obj, dict):
                    if obj.get("linked_to"):
                        linked_to_values = [
                            ["linked_to", ref["pk"], ref["resource_type"], ref["title"]]
                            for ref in obj["linked_to"]
                            if isinstance(ref, dict)
                        ]
                    if obj.get("linked_by"):
                        linked_by_values = [
                            ["linked_by", ref["pk"], ref["resource_type"], ref["title"]]
                            for ref in obj["linked_by"]
                            if isinstance(ref, dict)
                        ]
                print(linked_to_values + linked_by_values)
            return {}
        except Exception as e:
            logging.error(f"Error in cmd_describe: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Error in cmd_describe: {e}")
            return {"error": str(e)}

    def get(self, pk: int, **kwargs: Any) -> Optional[Dict[str, Any]]:
        try:
            endpoint = f"resources/{pk}/linked_resources"
            result = self.base.http_get(endpoint=endpoint)
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in get: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in get: {e}")
            return {"error": str(e)}


# --- Thesauri Keyword Label Get Capability ---
class KeywordLabelGetCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def get(self, pk: int, **kwargs: Any) -> Optional[Dict[str, Any]]:
        try:
            r = self.base.http_get(endpoint=f"tkeywordlabels?keyword={pk}")
            if not r or not isinstance(r, dict):
                return None
            labels = r.get("ThesaurusKeywordLabels") if r else None
            if isinstance(labels, dict):
                return labels
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in keyword label get: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in keyword label get: {e}")
            return {"error": str(e)}


# --- User Describe, Patch, Create Capabilities ---


class UserDescribeCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def cmd_describe(
        self,
        pk: int,
        user_resources: bool = False,
        user_groups: bool = False,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            obj = self.get(
                pk, user_resources=user_resources, user_groups=user_groups, **kwargs
            )
            if obj is None:
                logging.warning("describe user failed ... ")
            elif user_resources is True and obj is not None:
                print(obj.get("resources", obj))
            else:
                print(obj)
        except Exception as e:
            logging.error(f"Error in user cmd_describe: {e}")
            return {"error": str(e)}
        return None

    def get(
        self,
        pk: int,
        user_resources: bool = False,
        user_groups: bool = False,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            if user_resources and user_groups:
                raise AttributeError(
                    "cannot handle user_resources and user_groups True at the same time ..."
                )
            params = self.base._handle_params(kwargs)
            if user_groups is True:
                result = self.base.http_get(endpoint=f"users/{pk}/groups")
                if isinstance(result, dict):
                    return result
                return None
            elif user_resources is True:
                result = self.base.http_get(endpoint="resources", params=params)
                if isinstance(result, dict):
                    return result
                return None
            else:
                r = self.base.http_get(endpoint=f"users/{pk}", params=params)
                if isinstance(r, dict):
                    user = r.get("user")
                    if isinstance(user, dict):
                        return user
                    return r
                return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in user get: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in user get: {e}")
            return {"error": str(e)}


class UserPatchCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def cmd_patch(
        self,
        pk: int,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            json_content = None
            if json_path:
                with open(json_path, "r") as file:
                    try:
                        json_content = json.load(file)
                    except json.decoder.JSONDecodeError as E:
                        print(f"JSON decode error: {E}")
            elif fields:
                try:
                    json_content = json.loads(fields)
                except json.decoder.JSONDecodeError as E:
                    print(f"JSON decode error: {E}")
            if json_content is None:
                raise ValueError(
                    "At least one of 'fields' or 'json_path' must be provided."
                )
            obj = self.patch(pk=pk, json_content=json_content, **kwargs)
            print(obj)
        except Exception as e:
            logging.error(f"Error in user cmd_patch: {e}")
            return {"error": str(e)}
        return None

    def patch(
        self, pk: int, json_content: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        try:
            result = self.base.http_patch(endpoint=f"users/{pk}/", data=json_content)
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in user patch: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in user patch: {e}")
            return {"error": str(e)}


class UserCreateCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def cmd_create(
        self,
        username: Optional[str] = None,
        email: str = "",
        first_name: str = "",
        last_name: str = "",
        is_superuser: bool = False,
        is_staff: bool = False,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            json_content = None
            if json_path:
                with open(json_path, "r") as file:
                    try:
                        json_content = json.load(file)
                    except json.decoder.JSONDecodeError as E:
                        print(f"JSON decode error: {E}")
            elif fields:
                try:
                    json_content = json.loads(fields)
                except json.decoder.JSONDecodeError as E:
                    print(f"JSON decode error: {E}")
            obj = self.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_superuser=is_superuser,
                is_staff=is_staff,
                json_content=json_content,
                **kwargs,
            )
            print(obj)
        except Exception as e:
            logging.error(f"Error in user cmd_create: {e}")
            return {"error": str(e)}
        return None

    def create(
        self,
        username: Optional[str] = None,
        email: str = "",
        first_name: str = "",
        last_name: str = "",
        is_superuser: bool = False,
        is_staff: bool = False,
        json_content: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            if json_content is None:
                if username is None:
                    logging.error("missing username for user creation ...")
                    raise ValueError("missing username for user creation ...")
                json_content = {
                    "username": username,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                }
            result = self.base.http_post(endpoint="users", json=json_content)
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in user create: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in user create: {e}")
            return {"error": str(e)}


# --- Dataset Upload Capability ---
class UploadCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def cmd_upload(
        self,
        file_path: Path,
        charset: str = "UTF-8",
        time: bool = False,
        mosaic: bool = False,
        overwrite_existing_layer: bool = False,
        skip_existing_layers: bool = False,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            r = self.upload(
                file_path=file_path,
                charset=charset,
                time=time,
                mosaic=mosaic,
                overwrite_existing_layer=overwrite_existing_layer,
                skip_existing_layers=skip_existing_layers,
                **kwargs,
            )
            if not r or not isinstance(r, dict) or "execution_id" not in r:
                raise SystemExit(f"unexpected API response ...\n{r}")
            print(r)
        except Exception as e:
            logging.error(f"Error in cmd_upload: {e}")
            return {"error": str(e)}
        return None

    def upload(
        self,
        file_path: Path,
        charset: str = "UTF-8",
        time: bool = False,
        mosaic: bool = False,
        overwrite_existing_layer: bool = False,
        skip_existing_layers: bool = False,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        try:
            files: List[Any] = []
            dataset_path = file_path
            if dataset_path.suffix == ".shp":
                dbf_file = Path(
                    os.path.join(dataset_path.parent, dataset_path.stem + ".dbf")
                )
                shx_file = Path(
                    os.path.join(dataset_path.parent, dataset_path.stem + ".shx")
                )
                prj_file = Path(
                    os.path.join(dataset_path.parent, dataset_path.stem + ".prj")
                )
                if not all(
                    x.exists() for x in [dataset_path, dbf_file, shx_file, prj_file]
                ):
                    raise FileNotFoundError
                files = [
                    (
                        "base_file",
                        (
                            dataset_path.name,
                            open(dataset_path, "rb"),
                            "application/octet-stream",
                        ),
                    ),
                    (
                        "dbf_file",
                        (
                            dbf_file.name,
                            open(dbf_file, "rb"),
                            "application/octet-stream",
                        ),
                    ),
                    (
                        "shx_file",
                        (
                            shx_file.name,
                            open(shx_file, "rb"),
                            "application/octet-stream",
                        ),
                    ),
                    (
                        "prj_file",
                        (
                            prj_file.name,
                            open(prj_file, "rb"),
                            "application/octet-stream",
                        ),
                    ),
                ]
            else:
                if not dataset_path.exists():
                    raise FileNotFoundError
                files = [
                    (
                        "base_file",
                        (
                            dataset_path.name,
                            open(dataset_path, "rb"),
                            "application/octet-stream",
                        ),
                    )
                ]
                if dataset_path.suffix == ".zip":
                    files.append(
                        (
                            "zip_file",
                            (
                                dataset_path.name,
                                open(dataset_path, "rb"),
                                "application/octet-stream",
                            ),
                        )
                    )
            json_data = {
                "permissions": '{ "users": {"AnonymousUser": ["view_resourcebase"]} , "groups":{}}',
                "mosaic": mosaic,
                "time": str(time),
                "charset": charset,
                "non_interactive": True,
                "overwrite_existing_layer": overwrite_existing_layer,
                "skip_existing_layers": skip_existing_layers,
            }
            result = self.base.http_post(
                endpoint="uploads/upload",
                files=files,
                data=json_data,
            )
            if isinstance(result, dict):
                return result
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in upload: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in upload: {e}")
            return {"error": str(e)}


# --- Resource Metadata Capability ---
SUPPORTED_METADATA_TYPES = ["Atom", "DIF", "Dublin Core", "FGDC", "ISO"]
DEFAULT_METADATA_TYPE = "ISO"


class MetadataCapable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def cmd_metadata(
        self, pk: int, metadata_type: str = DEFAULT_METADATA_TYPE, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        try:
            r = self.metadata(pk=pk, metadata_type=metadata_type, **kwargs)
            if r is None:
                logging.warning("metadata download failed ... ")
                return None
            print(r.text if hasattr(r, "text") else r)
        except Exception as e:
            logging.error(f"Error in cmd_metadata: {e}")
            return {"error": str(e)}
        return None

    def metadata(
        self, pk: int, metadata_type: str = DEFAULT_METADATA_TYPE, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        try:
            r = self.base.http_get(endpoint=f"resources/{pk}")
            if not r or not isinstance(r, dict):
                return {"error": "No resource returned"}
            resource = r["resource"] if "resource" in r else r
            links = resource.get("links") if isinstance(resource, dict) else None
            if not links or not isinstance(links, list):
                return {"error": "No links found in resource"}
            link = None
            for m in links:
                if isinstance(m, dict) and m.get("name") == metadata_type:
                    link = m.get("url")
                    break
            if not link:
                return {"error": f"No link found for metadata type {metadata_type}"}
            if hasattr(self.base, "http_get_download"):
                result = self.base.http_get_download(link)
                if isinstance(result, dict):
                    return result
                return None
            resp = requests.get(link)
            if hasattr(resp, "text"):
                return {"text": resp.text}
            return None
        except requests.RequestException as e:
            logging.error(f"HTTP error in metadata: {e}")
            return {"error": str(e)}
        except Exception as e:
            logging.error(f"Unexpected error in metadata: {e}")
            return {"error": str(e)}


class Listable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def list(self, **kwargs: Any) -> Any:
        endpoint = f"{self.base.endpoint}/"
        params = self.base._handle_params(kwargs)
        r = self.base.http_get(endpoint=endpoint, params=params)
        if r is None:
            print("API call returned None")
            return None
        if not isinstance(r, dict):
            print(f"API call did not return a dict: {r}")
            return r
        obj = r.get(self.base.json_object_name)
        # Choose pretty table output for known types
        if obj is not None:
            # If obj is a dict, try to extract the list using common keys or json_object_name
            if isinstance(obj, dict):
                # Try common keys for paginated APIs
                for key in ("objects", "results", "items", "features", "data", self.base.json_object_name):
                    if key in obj and isinstance(obj[key], list):
                        obj = obj[key]
                        break
            if isinstance(obj, list):
                if self.base.endpoint == "datasets":
                    from .geonodetypes import GeonodeCmdOutNestedKey
                    print_list_on_cmd(
                        obj,
                        [
                            GeonodeCmdOutListKey(key="pk"),
                            GeonodeCmdOutListKey(key="title"),
                            GeonodeCmdOutNestedKey("owner.username"),
                            GeonodeCmdOutListKey(key="date"),
                        ],
                    )
                elif self.base.endpoint == "users":
                    print_list_on_cmd(
                        obj,
                        [
                            GeonodeCmdOutListKey(key="pk"),
                            GeonodeCmdOutListKey(key="username"),
                            GeonodeCmdOutListKey(key="email"),
                        ],
                    )
                else:
                    print(json.dumps(obj, indent=2))
                return obj
        print(f"Expected key '{self.base.json_object_name}' not found in response: {r}")
        return r
        print(f"Expected key '{self.base.json_object_name}' not found in response: {r}")
        return r


class Deletable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def delete(self, pk: str, **kwargs: Any) -> List[Any]:
        pks = self.base._parse_pk_string(pk)
        results = []
        for pk_item in pks:
            result = self.base.http_delete(endpoint=f"{self.base.endpoint}/{pk_item}")
            results.append(result)
        return results


class Patchable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def patch(self, pk: int, fields: Dict[str, Any], **kwargs: Any) -> Any:
        # This method should be implemented in a subclass or injected base
        return None


class Describable:
    def __init__(self, base: Any) -> None:
        self.base = base

    def describe(self, pk: int, **kwargs: Any) -> Any:
        # This method should be implemented in a subclass or injected base
        return None


# Add more capabilities as needed (Uploadable, Searchable, etc.)
