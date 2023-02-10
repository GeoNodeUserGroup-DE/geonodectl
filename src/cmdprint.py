from typing import List
from tabulate import tabulate


def show_list(headers: List[str], values: List[List[str]], tablefmt="github"):
    """_summary_: prints pretty table to commandline

    Args:
        headers (List[str]): header of the table
        values (List[List[str]]): list of lists of str of the value of the table. Each list a row in the table
        tablefmt (str, optional): used tabulate table format, see https://pypi.org/project/tabulate/
    """
    print(tabulate(values, headers=headers, tablefmt=tablefmt))
