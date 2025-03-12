import importlib.metadata as importlib_metadata

from jsync.jsync import synchronize
from jsync.rsync import RSync
from jsync.syncer import Syncer

__version__ = importlib_metadata.version(__name__)

__all__ = ["RSync", "Syncer", "synchronize"]
