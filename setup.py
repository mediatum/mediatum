# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from setuptools import setup, find_packages

setup(
    name="mediatum",
    version="2020.04",
    description="mediaTUM",
    url='https://mediatum.github.io/mediatum',
    author='mediaTUM authors, see git log',
    author_email='mediatum@ub.tum.de',
    license='GNU AFFERO GENERAL PUBLIC LICENSE v3 (AGPLv3)',
    classifiers=[
        'Intended Audience :: Customer Service',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU AFFERO GENERAL PUBLIC LICENSE v3 (AGPLv3)',
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
