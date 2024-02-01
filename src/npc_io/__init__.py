"""
Path, IO and caching tools for MindScope Neuropixels projects, compatible with
data in the cloud.
"""

import doctest
import importlib.metadata
import logging

import dotenv

from npc_io.cached_property import *
from npc_io.file_io import *
from npc_io.lazy_dict import *
from npc_io.types import *

logger = logging.getLogger(__name__)

__version__ = importlib.metadata.version("npc_io")
logger.debug(f"{__name__}.{__version__ = }")


def load_dotenv() -> None:
    """
    Load environment variables from .env file in current working directory.

    >>> load_dotenv()
    """
    is_dotenv_used = dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))
    logger.debug(f"environment variables loaded from dotenv file: {is_dotenv_used}")


load_dotenv()


def testmod(**testmod_kwargs) -> doctest.TestResults:
    """
    Run doctests for the module, configured to ignore exception details and
    normalize whitespace.

    Accepts kwargs to pass to doctest.testmod().

    Add to modules to run doctests when run as a script:
    .. code-block:: text
        if __name__ == "__main__":
            from npc_io import testmod
            testmod()
    """
    _ = testmod_kwargs.setdefault(
        "optionflags", doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    )
    return doctest.testmod(**testmod_kwargs)


if __name__ == "__main__":
    testmod()
