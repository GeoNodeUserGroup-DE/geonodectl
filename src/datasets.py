import os
from pathlib import Path
from typing import List, Dict

from src.resources import GeonodeResourceHandler
from src.geonodetypes import GeonodeHTTPFile
from src.cmdprint import show_list
from src.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey
from src.executionrequest import GeonodeExecutionRequestHandler


class GeonodeDatasetsHandler(GeonodeResourceHandler):
    """docstring for GeonodeDatasetsHandler"""

    ENDPOINT_NAME = JSON_OBJECT_NAME = "datasets"
    SINGULAR_RESOURCE_NAME = "dataset"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="date"),
        GeonodeCmdOutListKey(key="is_approved"),
        GeonodeCmdOutListKey(key="is_published"),
        GeonodeCmdOutListKey(key="state"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]

    def cmd_upload(
        self,
        title: str,
        file_path: Path,
        charset: str = "UTF-8",
        time: bool = False,
        mosaic: bool = False,
        **kwargs,
    ):
        """upload data and show them on the cmdline

        Args:
            title (str): title of the new dataset
            file_path (Path): Path to the file to upload.
            charset (str, optional): charset of data Defaults to "UTF-8".
            time (bool, optional): set if data is timeseries data Defaults to False.
            mosaic (bool, optional): declare dataset as mosaic
        """
        r = self.upload(
            title=title,
            file_path=file_path,
            charset=charset,
            time=time,
            mosaic=mosaic,
            **kwargs,
        )
        if "execution_id" not in r:
            raise SystemExit(f"unexpected API response ...\n{r}")

        execution_request_handler = GeonodeExecutionRequestHandler(
            env=self.gn_credentials
        )
        er = execution_request_handler.get(exec_id=str(r["execution_id"]), **kwargs)

        if kwargs["json"] is True:
            self.print_json(er)
        else:
            list_items = [
                ["exec_id", str(er["exec_id"])],
                ["status", str(er["status"])],
                ["created", str(er["created"])],
                ["name", str(er["name"])],
                ["link", str(er["link"])],
            ]
            show_list(values=list_items, headers=["key", "value"])

    def upload(
        self,
        file_path: Path,
        charset: str = "UTF-8",
        time: bool = False,
        mosaic: bool = False,
        **kwargs,
    ) -> Dict:
        """Upload dataset to geonode.

        Args:
            file_path (Path): Path to the file to upload. If shape make sure to set
                  the shp file and add place other files with same name next to the given
            title (str): title of the new dataset
            charset (str, optional): Fileencoding Defaults to "UTF-8".
            time (bool, optional): True if the dataset is a timeseries dataset. Defaults to False.
            mosaic (bool, optional): declare dataset as mosaic

        Raises:
            FileNotFoundError: raised when given file is not found
        """
        dataset_path: Path = file_path
        files: List[GeonodeHTTPFile] = []
        # handle shape files different
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

            if not any(x.exists for x in [dataset_path, dbf_file, shx_file, prj_file]):
                raise FileNotFoundError

            content_length: int = sum(
                [
                    os.path.getsize(f)
                    for f in [dataset_path, dbf_file, shx_file, prj_file]
                ]
            )

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
                    (dbf_file.name, open(dbf_file, "rb"), "application/octet-stream"),
                ),
                (
                    "shx_file",
                    (shx_file.name, open(shx_file, "rb"), "application/octet-stream"),
                ),
                (
                    "prj_file",
                    (prj_file.name, open(prj_file, "rb"), "application/octet-stream"),
                ),
            ]

        else:
            if not dataset_path.exists():
                raise FileNotFoundError
            content_length = os.path.getsize(dataset_path)

            files = [
                ("base_file", (dataset_path.name, open(dataset_path, "rb"))),
            ]

        params = {
            # layer permissions
            "permissions": '{ "users": {"AnonymousUser": ["view_resourcebase"]} , "groups":{}}',
            "mosaic": mosaic,
            "time": str(time),
            "charset": charset,
            "non_interactive": True,
        }

        return self.http_post(
            endpoint="uploads/upload",
            files=files,
            params=params,
            content_length=content_length,
        )
