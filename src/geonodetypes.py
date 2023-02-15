from typing import TypeAlias, Type, Tuple, Union, List

from dataclasses import dataclass
from abc import abstractmethod
import io


class GeonodeCmdOutObjectKey:
    @abstractmethod
    def get_key(self, ds: dict):
        raise NotImplementedError


@dataclass
class GeonodeCmdOutListKey(GeonodeCmdOutObjectKey):
    key: str
    type: Type = list

    def __str__(self) -> str:
        return self.key

    def get_key(self, ds: dict):
        return ds[self.key]


GeonodeCmdOutputKeys: TypeAlias = List[GeonodeCmdOutObjectKey]


@dataclass
class GeonodeCmdOutDictKey(GeonodeCmdOutObjectKey):
    key: List[str]
    type: Type = dict

    def __str__(self) -> str:
        return ".".join(self.key)

    def get_key(self, ds: dict):
        for k in self.key:
            ds = ds[k]
        return ds


GeonodeHTTPFile: TypeAlias = Tuple[
    str, Union[Tuple[str, io.BufferedReader], Tuple[str, io.BufferedReader, str]]
]


@dataclass
class GeonodeEnv:
    url: str
    auth_basic: str
    verify: bool
