from typing import TypeAlias, Type, Tuple, Union, List
from dataclasses import dataclass
from abc import abstractmethod
import io


class GeonodeCmdOutObjectKey:
    @abstractmethod
    def get_key(self, ds: dict):
        """
        Get the key from the given dictionary.

        Parameters:
            ds (dict): The dictionary to extract the key from.

        Raises:
            NotImplementedError: This method is meant to be overridden by subclasses.

        Returns:
            None
        """
        raise NotImplementedError


@dataclass
class GeonodeCmdOutListKey(GeonodeCmdOutObjectKey):
    key: str
    type: Type = list

    def __str__(self) -> str:
        """
        Return a string representation of the object.
        """
        return self.key

    def get_key(self, ds: dict):
        """
        Get the value associated with the given key from the given dictionary.

        Args:
            ds (dict): The dictionary to retrieve the value from.

        Returns:
            The value associated with the key in the dictionary.
        """
        return ds[self.key]


GeonodeCmdOutputKeys: TypeAlias = List[GeonodeCmdOutObjectKey]


@dataclass
class GeonodeCmdOutDictKey(GeonodeCmdOutObjectKey):
    key: List[str]
    type: Type = dict

    def __str__(self) -> str:
        """
        Returns a string representation of the object.

        :return: The string representation.
        :rtype: str
        """
        return ".".join(self.key)

    def get_key(self, ds: dict):
        """
        Get the value from a nested dictionary using a list of keys.

        Args:
            ds (dict): The nested dictionary.

        Returns:
            The value obtained by accessing the nested dictionary using the list of keys.
        """
        for k in self.key:
            ds = ds[k]
        return ds


GeonodeHTTPFile: TypeAlias = Tuple[
    str, Union[Tuple[str, io.BufferedReader], Tuple[str, io.BufferedReader, str]]
]
