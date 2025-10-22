from typing import Any, Dict
import requests


class HandlerBase:

    def http_post(
        self,
        endpoint: str,
        data: Dict = None,
        files=None,
        json=None,
        content_length=None,
    ):
        url = self.env["url"].rstrip("/") + "/" + endpoint.lstrip("/")
        headers = {"Authorization": f"Basic {self.env['basic']}"}
        if json is not None:
            headers["Content-Type"] = "application/json"
        kwargs = {"headers": headers, "verify": False}
        if files:
            kwargs["files"] = files
            kwargs["data"] = data
        elif json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data
        resp = requests.post(url, **kwargs)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text

    def http_get_download(self, url: str):
        headers = {"Authorization": f"Basic {self.env['basic']}"}
        resp = requests.get(url, headers=headers, verify=False)
        resp.raise_for_status()
        return resp

    def __init__(self, env, endpoint: str, json_object_name: str):
        self.env = env
        self.endpoint = endpoint
        self.json_object_name = json_object_name
        # You may want to initialize http_get, http_patch, etc. here or via composition

    def http_get(self, endpoint: str, params: Dict = None):
        url = self.env["url"].rstrip("/") + "/" + endpoint.lstrip("/")
        headers = {"Authorization": f"Basic {self.env['basic']}"}
        resp = requests.get(url, headers=headers, params=params, verify=False)
        resp.raise_for_status()
        return resp.json()

    def http_patch(self, endpoint: str, data: Dict):
        url = self.env["url"].rstrip("/") + "/" + endpoint.lstrip("/")
        headers = {
            "Authorization": f"Basic {self.env['basic']}",
            "Content-Type": "application/json",
        }
        resp = requests.patch(url, headers=headers, json=data, verify=False)
        resp.raise_for_status()
        return resp.json()

    def http_delete(self, endpoint: str):
        url = self.env["url"].rstrip("/") + "/" + endpoint.lstrip("/")
        headers = {"Authorization": f"Basic {self.env['basic']}"}
        resp = requests.delete(url, headers=headers, verify=False)
        resp.raise_for_status()
        return resp.status_code

    def _handle_params(self, kwargs: Dict) -> Dict:
        # Placeholder for param handling logic
        return kwargs

    def _parse_pk_string(self, pk: str):
        # Placeholder for pk parsing logic (range, list, single)
        if "-" in pk:
            start, end = map(int, pk.split("-"))
            return list(range(start, end + 1))
        elif "," in pk:
            return [int(x) for x in pk.split(",")]
        else:
            return [int(pk)]
