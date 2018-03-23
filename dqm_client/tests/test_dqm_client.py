"""
Unit and regression test for the dqm_client package.
"""

# Import package, test suite, and other packages as needed
import dqm_client
import pytest
import sys

def test_dqm_client_imported():
    """Sample test, will always pass so long as import statement worked"""
    assert "dqm_client" in sys.modules
