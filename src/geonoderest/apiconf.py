from pathlib import Path
from typing import Optional
import os

from dataclasses import dataclass


@dataclass
class GeonodeApiConf:
    url: str
    auth_basic: str
    verify: bool

    @staticmethod
    def from_env_file(path: Path) -> "GeonodeApiConf":
        """
        Creates a new GeonodeApiConf object from a .env file
        """
        url: Optional[str] = None
        auth_basic: Optional[str] = None
        verify: Optional[bool] = None

        with path.open("r") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip()
                if key == "GEONODE_API_URL":
                    url = value
                if key == "GEONODE_API_BASIC_AUTH":
                    auth_basic = value
                if key == "GEONODE_API_VERIFY":
                    verify = value == "True"

        missing = [
            name
            for name, val in [
                ("GEONODE_API_URL", url),
                ("GEONODE_API_BASIC_AUTH", auth_basic),
            ]
            if val is None
        ]
        if missing:
            raise SystemExit(
                f"Missing required keys in env file {path}: {', '.join(missing)}"
            )

        return GeonodeApiConf(
            url=url,  # type: ignore[arg-type]
            auth_basic=auth_basic,  # type: ignore[arg-type]
            verify=verify if verify is not None else True,
        )

    @staticmethod
    def from_env_vars() -> "GeonodeApiConf":
        """
        Creates a new GeonodeApiConf object from environment variables
        """
        if (
            "GEONODE_API_URL" not in os.environ
            or "GEONODE_API_BASIC_AUTH" not in os.environ
        ):
            raise SystemExit(
                "env vars not set: GEONODE_API_URL, GEONODE_API_BASIC_AUTH"
            )

        url = os.getenv("GEONODE_API_URL", "")
        auth_basic = os.getenv("GEONODE_API_BASIC_AUTH", "")
        verify = True if "True" == os.getenv("GEONODE_API_VERIFY", "True") else False
        return GeonodeApiConf(url=url, auth_basic=auth_basic, verify=verify)

    def get_geonode_base_url(self) -> str:
        return self.url[:-8]
