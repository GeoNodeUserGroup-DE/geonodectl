from typing import List, Union, Dict
from tabulate import tabulate
import json
import logging
import sys

from .geonodetypes import GeonodeCmdOutObjectKey

def show_list(headers: List[str], values: List[List[str]], tablefmt="github"):
    print(tabulate(values, headers=headers, tablefmt=tablefmt))

def __cmd_list_header__(cmdout_header: List[GeonodeCmdOutObjectKey]) -> List[str]:
    return [str(cmdoutkey) for cmdoutkey in cmdout_header]

def print_list_on_cmd(obj: Dict, cmdout_header: List[GeonodeCmdOutObjectKey]):
    def generate_line(i, obj: Dict, headers: List[GeonodeCmdOutObjectKey]) -> List:
        return [cmdoutkey.get_key(obj[i]) for cmdoutkey in headers]
    values = [generate_line(i, obj, cmdout_header) for i in range(len(obj))]
    show_list(headers=__cmd_list_header__(cmdout_header), values=values)

def print_json(json_str: Union[str, dict]):
    if json_str is None:
        logging.warning("return from geonode api was broken, not output ...")
        return None
    print(json.dumps(json_str, indent=2))

def json_decode_error_handler(json_str: str, error: json.decoder.JSONDecodeError):
    logging.error(f"Error decoding json string:\n {json_str} ...")
    logging.error(f"{error}")
    sys.exit(1)
