from setuptools import setup, find_packages
import codecs
import os
import re

here = os.path.abspath(os.path.dirname(__file__))

# Read the version number from a source file.
# Why read it, and not import?
# see https://groups.google.com/d/topic/pypa-dev/0PkjVpcxTzQ/discussion


def find_version(*file_paths):
    # Open in Latin-1 so that we avoid encoding errors.
    # Use codecs.open for Python 2 compatibility
    with codecs.open(os.path.join(here, *file_paths), 'r', 'latin1') as f:
        version_file = f.read()

    # The version line must have the form
    # __version__ = 'ver'
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="mediatum",
    version=find_version('core', '__init__.py'),
    description="mediaTUM",
    url='https://mediatum.github.io/mediatum',
    author='mediaTUM authors, see git log',
    author_email='mediatum@ub.tum.de',
    license='GNU General Public License v3 (GPLv3)',
    classifiers=[
        'Intended Audience :: Customer Service',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='',
    packages=find_packages(),
    install_requires=[],
    setup_requires=["setuptools-git"],
    include_package_data=True,

    entry_points={
        "console_scripts": [
            "mediatum-manage=bin.manage:main",
            "mediatum-backend=bin.mediatum:main"
        ]
    }
)
