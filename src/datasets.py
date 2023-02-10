import os
from pathlib import Path
from typing import List

from src.geonodeobject import (
    GeoNodeObject,
    GeonodeHTTPFile,
    GeonodeCmdOutListKey,
    GeonodeCmdOutDictKey,
)
from src.cmdprint import show_list


class GeonodeDatasets(GeoNodeObject):
    
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

    GET_CMDOUT_PROPERTIES = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="uuid"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="workspace"),
        GeonodeCmdOutListKey(key="store"),
        GeonodeCmdOutListKey(key="charset"),
        GeonodeCmdOutListKey(key="is_mosaic"),
        GeonodeCmdOutListKey(key="has_time"),
        GeonodeCmdOutListKey(key="has_elevation"),
        GeonodeCmdOutListKey(key="time_regex"),
        GeonodeCmdOutListKey(key="ows_url"),
        GeonodeCmdOutListKey(key="ptype"),
        GeonodeCmdOutDictKey(key=["default_style", "name"]),
        GeonodeCmdOutDictKey(key=["styles", "name"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="polymorphic_ctype_id"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutListKey(key="abstract"),
        GeonodeCmdOutListKey(key="attribution"),
        GeonodeCmdOutListKey(key="doi"),
        GeonodeCmdOutListKey(key="alternate"),
        GeonodeCmdOutListKey(key="abstract"),
        GeonodeCmdOutListKey(key="date"),
        GeonodeCmdOutListKey(key="date_type"),
        GeonodeCmdOutListKey(key="temporal_extent_start"),
        GeonodeCmdOutListKey(key="temporal_extent_end"),
        GeonodeCmdOutListKey(key="edition"),
        GeonodeCmdOutListKey(key="purpose"),
        GeonodeCmdOutListKey(key="maintenance_frequency"),
        GeonodeCmdOutListKey(key="constraints_other"),
        GeonodeCmdOutListKey(key="language"),
        GeonodeCmdOutListKey(key="supplemental_information"),
        GeonodeCmdOutListKey(key="data_quality_statement"),
        GeonodeCmdOutListKey(key="srid"),
        GeonodeCmdOutListKey(key="group"),
        GeonodeCmdOutListKey(key="popular_count"),
        GeonodeCmdOutListKey(key="share_count"),
        GeonodeCmdOutListKey(key="rating"),
        GeonodeCmdOutListKey(key="featured"),
        GeonodeCmdOutListKey(key="is_published"),
        GeonodeCmdOutListKey(key="is_approved"),
        GeonodeCmdOutListKey(key="detail_url"),
        GeonodeCmdOutListKey(key="created"),
        GeonodeCmdOutListKey(key="last_updated"),
        GeonodeCmdOutListKey(key="metadata_only"),
        GeonodeCmdOutListKey(key="processed"),
        GeonodeCmdOutListKey(key="state"),
        GeonodeCmdOutListKey(key="sourcetype"),
        GeonodeCmdOutListKey(key="embed_url"),
        GeonodeCmdOutListKey(key="thumbnail_url"),
        GeonodeCmdOutListKey(key="keywords"),
        GeonodeCmdOutListKey(key="tkeywords"),
        GeonodeCmdOutDictKey(key=["regions", "name"]),
        GeonodeCmdOutListKey(key="category"),
        GeonodeCmdOutListKey(key="restriction_code_type"),
        GeonodeCmdOutDictKey(key=["license", "identifier"]),
        GeonodeCmdOutListKey(key="spatial_representation_type"),
        GeonodeCmdOutListKey(key="is_copyable"),
        GeonodeCmdOutListKey(key="download_url"),
        GeonodeCmdOutListKey(key="favorite")
    ]

    RESOURCE_TYPE = "datasets"

    def cmd_upload(self, charset: str = "UTF-8", time: bool = False, **kwargs):
        """upload data and show them on the cmdline

        Args:
            charset (str, optional): charset of data Defaults to "UTF-8".
            time (bool, optional): set if data is timeseries data Defaults to False.
        """
        r = self.upload(charset=charset, time=time, **kwargs)
        if kwargs["json"] is True:
            import pprint

            pprint.pprint(r)
        else:
            list_items = [
                ["title", kwargs["title"]],
                ["success", str(r["success"])],
                ["status", r["status"]],
                ["bbox", r["bbox"] if "bbox" in r else ""],
                ["crs", r["crs"] if "crs" in r else ""],
                ["url", r["url"] if "url" in r else ""],
            ]
            show_list(values=list_items, headers=["key", "value"])

    def upload(
        self, charset: str = "UTF-8", time: bool = False, mosaic: bool = False, **kwargs
    ):
        """Upload dataset to geonode.

        Args:
            filepath_path (Path): Path to the file to upload. If shape make sure to set
                  the shp file and add place other files with same name next to the given
            title (str): title of the new dataset
            charset (str, optional): Fileencoding Defaults to "UTF-8".
            non_interactive (bool, optional): False if dataset is interactive. Defaults to True.
            time (bool, optional): True if the dataset is a timeseries dataset. Defaults to False.

        Raises:
            FileNotFoundError: raised when given file is not found
        """
        dataset_path: Path = kwargs["file_path"]
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
                    (dbf_file.name, open(dbf_file, "rb"),
                     "application/octet-stream"),
                ),
                (
                    "shx_file",
                    (shx_file.name, open(shx_file, "rb"),
                     "application/octet-stream"),
                ),
                (
                    "prj_file",
                    (prj_file.name, open(prj_file, "rb"),
                     "application/octet-stream"),
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
            "dataset_title": kwargs["title"],
            "abstract": kwargs["abstract"] if "abstract" in kwargs else "",
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
