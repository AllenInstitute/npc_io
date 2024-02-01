"""
Copy of stdlib functools.cached_property minus faulty thread lock.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Generic, TypeVar, overload

from typing_extensions import Self

_NOT_FOUND = object()
_T = TypeVar("_T")


class cached_property(functools.cached_property, Generic[_T]):
    """Copy of stdlib functools.cached_property minus faulty thread lock.

    Issue described here: https://github.com/python/cpython/issues/87634

    This version will make concurrent tasks across multiple instances faster, but
    each instance's cached properties will no longer be thread-safe - ie. don't
    dispatch the same instance to multiple threads without implementing your own
    lock.


    Examples:
    .. code-block:: text
        >>> import random
        >>> class Test:
        ...     @cached_property
        ...     def cached_prop(self):
        ...         return random.random()
        >>> t = Test()
        >>> x = t.cached_prop
        >>> assert x == t.cached_prop

        # note: like the built-in property, cached_properties can be overwritten:
        >>> t.cached_prop = 5
        >>> assert t.cached_prop == 5
    """

    func: Callable[[Any], _T]

    def __init__(self, func: Callable[[Any], _T]) -> None:
        super().__init__(func)

    @overload
    def __get__(self, instance: None, owner: type[Any] | None = None) -> Self: ...

    @overload
    def __get__(self, instance: object, owner: type[Any] | None = None) -> _T: ...

    def __get__(self, instance, owner=None) -> Self | _T | Any:
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it."
            )
        try:
            cache = instance.__dict__
        except (
            AttributeError
        ):  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        ## these lines are removed from the original cached_property ------
        # with self.lock:
        #     # check if another thread filled cache while we awaited lock
        #     val = cache.get(self.attrname, _NOT_FOUND)
        # -----------------------------------------------------------------
        if val is _NOT_FOUND:
            val = self.func(instance)
            try:
                cache[self.attrname] = val
            except TypeError:
                msg = (
                    f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                    f"does not support item assignment for caching {self.attrname!r} property."
                )
                raise TypeError(msg) from None
        return val


if __name__ == "__main__":
    from npc_io import testmod

    testmod()
