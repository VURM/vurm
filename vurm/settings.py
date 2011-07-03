"""
Configuration management for the different VURM components.
"""



import os
import ConfigParser



DEFAULT_FILES = [
    '/etc/vurm/vurm.conf',
    os.path.expanduser('~/.vurm.conf'),
]



def loadConfig(path=None, defaults=None):
    """
    Loads and parses an INI style configuration file using Python's built-in
    ConfigParser module.

    If path (t.p.filepath.Filepath instance) is specified, load it.

    If ``defaults`` (a list of strings) is given, try to load each entry as a
    file, without throwing any error if the operation fails.

    If ``defaults`` is not given, the following locations are tried:

     * /etc/vurm/vurm.conf
     * ~/.vurm.conf

    To completely disable defaults loading, pass in an empty list or ``False``.

    Returns the SafeConfigParser instance used to load and parse the files.
    """

    if defaults is None:
        defaults = DEFAULT_FILES

    config = ConfigParser.SafeConfigParser()

    if defaults:
        config.read(defaults)

    if path:
        config.readfp(path.open())

    return config
