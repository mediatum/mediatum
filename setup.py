from setuptools import setup, find_packages

setup(
    name="mediatum",
    version="2020.04",
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
