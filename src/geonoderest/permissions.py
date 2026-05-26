from typing import Dict, Optional

from geonoderest.rest import GeonodeRest
from geonoderest.executionrequest import GeonodeExecutionRequestHandler


class GeonodePermissionsHandler(GeonodeRest):
    """GET / PUT /api/v2/resources/{pk}/permissions.

    The PUT endpoint is asynchronous: the response carries an
    ``execution_id`` and ``status_url`` rather than the applied state.
    Callers should invoke :meth:`wait_for_completion` (or poll the
    ``execution_id`` themselves) before assuming the change is visible to
    downstream readers.
    """

    def get(self, pk: int) -> Optional[Dict]:
        """Return the current permission set for a resource.

        Args:
            pk (int): Resource primary key.

        Returns:
            Dict with keys ``users``, ``groups``, ``organizations``, each
            holding a list of entries with id, name, and permission level,
            or None on error.
        """
        return self.http_get(endpoint=f"resources/{pk}/permissions")

    def set(self, pk: int, payload: Dict) -> Optional[Dict]:
        """Submit a new permission set. Returns the async receipt.

        The receipt has the shape::

            {
              "status": "ready",
              "execution_id": "<uuid>",
              "status_url": "<absolute url>"
            }

        Pass the ``execution_id`` to :meth:`wait_for_completion` to block
        until the permission change has been applied.
        """
        return self.http_put(
            endpoint=f"resources/{pk}/permissions", json_content=payload
        )

    def wait_for_completion(
        self,
        exec_id: str,
        poll_interval: int = 2,
        timeout: int = 120,
        on_poll=None,
    ) -> Dict:
        """Poll an in-flight permission change until it reaches a terminal state.

        Delegates to :class:`GeonodeExecutionRequestHandler` so the polling
        behavior matches uploads and async deletes.
        """
        handler = GeonodeExecutionRequestHandler(env=self.gn_credentials)
        return handler.wait_for_completion(
            exec_id=exec_id,
            poll_interval=poll_interval,
            timeout=timeout,
            on_poll=on_poll,
        )
