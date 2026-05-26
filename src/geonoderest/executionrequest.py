from typing import Dict, List, Optional
import logging
import time

from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutObjectKey
from geonoderest.rest import GeonodeRest
from geonoderest.exceptions import GeoNodeRestException

from geonoderest.cmdprint import print_list_on_cmd, print_json

TERMINAL_STATUSES = ("finished", "failed")


class GeonodeExecutionRequestHandler(GeonodeRest):
    ENDPOINT_NAME = "executionrequest"
    JSON_OBJECT_NAME = "requests"
    SINGULAR_RESOURCE_NAME = "request"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutObjectKey] = [
        GeonodeCmdOutListKey(key="exec_id"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="status"),
        GeonodeCmdOutListKey(key="user"),
        GeonodeCmdOutListKey(key="source"),
        GeonodeCmdOutListKey(key="created"),
        GeonodeCmdOutListKey(key="log"),
    ]

    def cmd_describe(self, exec_id: str, **kwargs):
        obj = self.get(exec_id=exec_id, **kwargs)
        print_json(obj)

    def get(self, exec_id: str, **kwargs) -> Dict:
        """
        get details for a given exec_id

        Args:
            exec_id (str): exec_id of the object

        Returns:
            Dict: obj details
        """
        r = self.http_get(endpoint=f"{self.ENDPOINT_NAME}/{exec_id}")
        return r[self.SINGULAR_RESOURCE_NAME]

    def cmd_list(self, **kwargs):
        """show list of geonode obj on the cmdline"""
        obj = self.list(**kwargs)
        if obj is None:
            logging.warning("getting list failed ...")
            return None
        if kwargs["json"]:
            print_json(obj)
        else:
            print_list_on_cmd(obj, self.LIST_CMDOUT_HEADER)

    def list(self, **kwargs) -> Optional[Dict]:
        """returns dict of execution requests from geonode

        Returns:
            Dict: request response
        """
        endpoint = f"{self.ENDPOINT_NAME}/"

        params = self.__handle_http_params__({}, kwargs)
        r = self.http_get(endpoint=endpoint, params=params)
        if r is None:
            return None
        return r[self.JSON_OBJECT_NAME]

    def wait_for_completion(
        self,
        exec_id: str,
        poll_interval: int = 2,
        timeout: int = 600,
        on_poll=None,
    ) -> Dict:
        """Poll an execution request until it reaches a terminal status.

        Used by any async-acknowledged operation that returns an execution_id:
        uploads, async resource deletes, permission changes, etc.

        Args:
            exec_id (str): Execution request UUID.
            poll_interval (int): Seconds between polls. Defaults to 2.
            timeout (int): Max seconds to wait before giving up. Defaults to 600.
            on_poll (callable, optional): Invoked with the latest record after
                each poll. Useful for surfacing progress to the user.

        Returns:
            Dict: The terminal execution record (status == "finished").

        Raises:
            GeoNodeRestException: If the execution reports `failed` or the
                timeout elapses before reaching a terminal status.
        """
        elapsed = 0
        last: Optional[Dict] = None
        while elapsed <= timeout:
            er = self.get(exec_id=exec_id)
            if er is None:
                raise GeoNodeRestException(
                    f"execution {exec_id} not found while polling"
                )
            last = er
            status = (er.get("status") or "").lower()
            if on_poll is not None:
                on_poll(er)
            if status == "finished":
                logging.info(f"execution {exec_id} finished in ~{elapsed}s")
                return er
            if status == "failed":
                raise GeoNodeRestException(
                    f"execution {exec_id} failed: "
                    f"{er.get('log') or er.get('output_params')}"
                )
            logging.debug(
                f"waiting for execution {exec_id} (status={status}, "
                f"elapsed={elapsed}s) ..."
            )
            time.sleep(poll_interval)
            elapsed += poll_interval
        raise GeoNodeRestException(
            f"execution {exec_id} did not reach a terminal status within "
            f"{timeout}s (last status: {last.get('status') if last else 'unknown'})"
        )
