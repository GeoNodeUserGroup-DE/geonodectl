from pathlib import Path
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
        with path.open("r") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=")
                if key == "GEONODE_API_URL":
                    url = value
                if key == "GEONODE_API_BASIC_AUTH":
                    auth_basic = value
                if key == "GEONODE_API_VERIFY":
                    verify = value == "True"
        return GeonodeApiConf(url=url, auth_basic=auth_basic, verify=verify)

    @staticmethod
    def from_env_vars() -> "GeonodeApiConf":
        """
        Creates a new GeonodeApiConf object from environment variables
        """
        if (
            not "GEONODE_API_URL" in os.environ
            or "GEONODE_API_BASIC_AUTH" not in os.environ
        ):
            raise SystemExit(
                "env vars not set: GEONODE_API_URL, GEONODE_API_BASIC_AUTH"
            )

        url = os.getenv("GEONODE_API_URL", "")
        auth_basic = os.getenv("GEONODE_API_BASIC_AUTH", "")
        verify = True if "True" == os.getenv("GEONODE_API_VERIFY", "True") else False
        return GeonodeApiConf(url=url, auth_basic=auth_basic, verify=verify)
