"""
Configuration management for the different VURM components.
"""



import os
import ConfigParser



def loadConfig(path=None, loadDefaults=True):
    """
    Loads and parses an INI style configuration file using Python's buil-in
    ConfigParser module.

    If path (t.p.filepath.Filepath instance) is specified, load it.

    If loadDefaults is True (the default), try to load defaults from the
    following locations:

     * /etc/vurm/vurm.conf
     * ~/.vurm.conf

    Returns the SafeConfigParser instance used to load and parse the files.
    """

    config = ConfigParser.SafeConfigParser()

    if loadDefaults:
        config.read([
            '/etc/vurm/vurm.conf',
            os.path.expanduser('~/.vurm.conf'),

            # For testing only:
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests',
                    'config.ini'),
        ])

    if path:
        config.readfp(path.open())

    return config

