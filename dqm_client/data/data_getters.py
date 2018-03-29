"""
Assists in grabbing the requisite data
"""

import copy
import glob
import os

_data_dir = os.path.dirname(__file__)

_folders = ["molecules"]
_data_folders = {x: os.path.join(_data_dir, x) for x in _folders}

def _get_folder_path(folder):
    if folder not in _data_folders:
        raise KeyError("Folder '%s' not recognized" % folder)
    
    return _data_folders[folder]
        

def list_directories():
    """
    List all known directories.
    """
    return copy.deepcopy(_data_folders.keys())

def get_file_name(folder, filename=None):
    folder = _get_folder_path(folder) 
    if filename:
        folder = os.path.join(folder, filename)
    return glob.glob(folder)


def get_file(folder, *args):
    folder = _get_folder_path(folder) 
    filename = os.path.join(folder, *args)
    if not os.path.isfile(filename):
        raise OSError("Path '%s' not found." % filename)

    with open(filename, "r") as infile:
        ret = infile.read()

    return ret
