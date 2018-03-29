"""
dqm_client
A front-end client to DQM
"""

# Add imports here
from .molecule import Molecule
from .database import Database

from . import data
from . import schema

# Handle versioneer
from ._version import get_versions
versions = get_versions()
__version__ = versions['version']
__git_revision__ = versions['full-revisionid']
del get_versions, versions
