"""
Mapping class for postponed evaluation of functions and caching of results.
"""

from __future__ import annotations

import collections.abc
import contextlib
from collections.abc import Iterator
from typing import TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LazyDict(collections.abc.Mapping[K, V]):
    """Dict for postponed evaluation of functions and caching of results.

    Assign values as a tuple of (callable, args, kwargs). The callable will be
    evaluated when the key is first accessed. The result will be cached and
    returned directly on subsequent access.

    Effectively immutable after initialization.

    Examples:
    .. code-block:: text
        # input values in the form `tuple(callable, args: Sequence, kwargs: Mapping)`
        >>> import random
        >>> callable, args, kwargs = random.choice, (range(100),), {}

        # initialize with keyword arguments, like the built-in dict:
        >>> d = LazyDict(choice=(callable, args, kwargs))

        # or with a dict:
        >>> d = LazyDict({'choice': (callable, args, kwargs)})

        >>> d
        LazyDict(keys=['choice'])

        # values are only computed the first time they're accessed, then cached:
        >>> c = d['choice']
        >>> c                               # doctest: +SKIP
        5
        >>> c == d['choice']
        True


        # other immutable dict-like behavior:
        >>> len(d)
        1
        >>> [k for k in d]
        ['choice']
        >>> d.get('random') is None
        True
    """

    def __init__(self, *args, **kwargs) -> None:
        self._raw_dict = dict(*args, **kwargs)

    def __getitem__(self, key) -> V:
        with contextlib.suppress(TypeError):
            func, args, *kwargs = self._raw_dict.__getitem__(key)
            self._raw_dict.__setitem__(key, func(*args, **kwargs[0]))
        return self._raw_dict.__getitem__(key)

    def __iter__(self) -> Iterator[K]:
        return iter(self._raw_dict)

    def __len__(self) -> int:
        return len(self._raw_dict)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(keys={list(self._raw_dict.keys())})"


if __name__ == "__main__":
    from npc_io import testmod

    testmod()
