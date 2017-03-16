from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))

# Read the version number from a source file.
# Why read it, and not import?
# see https://groups.google.com/d/topic/pypa-dev/0PkjVpcxTzQ/discussion


def find_version():
    with open(os.path.join(here, 'VERSION')) as version_file:
        return version_file.read().strip()


setup(
    name="mediatum",
    version=find_version(),
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
