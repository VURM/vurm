import os
from setuptools import setup, find_packages


NAME = 'vurm'

VERSION = '0.1'

DESCRIPTION = """
Phsical resources management layer to provide SLURM with virtual resources.
"""

LICENSE = 'MIT'

URL = 'https://github.com/VURM/vurm'

AUTHOR = 'Jonathan Stoppani', 'jonathan@stoppani.name'

KEYWORDS = 'slurm vurm hpc batch cluster cloud virtual'

CLASSIFIERS = [

]


def read(fname, fail_silently=False):
    """
    Utility function to read the README file.
    """
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except:
        if not fail_silently:
            raise
        return ''


def get_files(*bases):
    """
    Utility function to list all files in a data directory.
    """
    for base in bases:
        basedir, _ = base.split('.', 1)
        base = os.path.join(os.path.dirname(__file__), *base.split('.'))
        
        rem = len(os.path.dirname(base))  + len(basedir) + 2
        
        for root, dirs, files in os.walk(base):
            for name in files:
                yield os.path.join(basedir, root, name)[rem:]


def requirements(fname):
    """
    Utility function to create a list of requirements from the output of the
    pip freeze command saved in a text file.
    """
    packages = read(fname).split('\n')
    packages = (p.strip() for p in packages)
    packages = (p for p in packages if p and not p.startswith('#'))
    return list(packages)


setup(
    name=NAME,
    version=VERSION,
    description=' '.join(DESCRIPTION.strip().splitlines()),
    long_description=read('README.md'),
    classifiers=CLASSIFIERS,
    keywords=KEYWORDS,
    author=AUTHOR[0],
    author_email=AUTHOR[1],
    url=URL,
    license=LICENSE,
    packages=find_packages(),
    package_data = {
        #'dcs': list(get_files('dcs.schemata', 'dcs.fabfiles')),
    },
    #install_requires=requirements('requirements.txt'),
    entry_points=read('entry-points.ini', True),
)
