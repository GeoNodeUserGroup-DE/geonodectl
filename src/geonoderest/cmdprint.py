from typing import List, Union, Dict
from tabulate import tabulate
import json
import logging
import sys

from .geonodetypes import GeonodeCmdOutObjectKey


def show_list(headers: List[str], values: List[List[str]], tablefmt="github"):
    """_summary_: prints pretty table to commandline

    Args:
        headers (List[str]): header of the table
        values (List[List[str]]): list of lists of str of the value of the table. Each list a row in the table
        tablefmt (str, optional): used tabulate table format, see https://pypi.org/project/tabulate/
    """
    print(tabulate(values, headers=headers, tablefmt=tablefmt))


def __cmd_list_header__(cmdout_header: List[GeonodeCmdOutObjectKey]) -> List[str]:
    """returns the default header to print list on cmd

    Returns:
        List[str]: list of header elements as str
    """
    return [str(cmdoutkey) for cmdoutkey in cmdout_header]


def print_list_on_cmd(obj: Dict, cmdout_header: List[GeonodeCmdOutObjectKey]):
    """print a beautiful list on the cmdline

    Args:
        obj (Dict): dict object to print on cmd line
    """

    def generate_line(i, obj: Dict, headers: List[GeonodeCmdOutObjectKey]) -> List:
        return [cmdoutkey.get_key(obj[i]) for cmdoutkey in headers]

    values = [generate_line(i, obj, cmdout_header) for i in range(len(obj))]
    show_list(headers=__cmd_list_header__(cmdout_header), values=values)


def print_json(json_str: Union[str, dict]):
    """
    Print the given JSON string or dictionary with an indentation of 2 spaces.

    Args:
        json_str (Union[str, dict]): The JSON string or dictionary to be printed.

    Returns:
        None
    """
    if json_str is None:
        logging.warning("return from geonode api was broken, not output ...")
        return None
    print(json.dumps(json_str, indent=2))


def json_decode_error_handler(json_str: str, error: json.decoder.JSONDecodeError):
    logging.error(f"Error decoding json string:\n {json_str} ...")
    logging.error(f"{error}")
    sys.exit(1)
