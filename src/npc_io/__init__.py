"""
    npc_io

    File IO tools for MindScope Neuropixels projects in the cloud.
    :author: Ben Hardcastle <ben.hardcastle@alleninstitue.org>
    :license: MIT
"""
import importlib.metadata
import logging

import dotenv

logger = logging.getLogger(__name__)

__version__ = importlib.metadata.version("npc_io")
logger.debug(f"{__name__}.{__version__ = }")

is_dotenv_used = dotenv.load_dotenv(
    dotenv.find_dotenv(usecwd=True)
)  # take environment variables from .env
logger.debug(f"environment variables used from dotenv file: {is_dotenv_used}")