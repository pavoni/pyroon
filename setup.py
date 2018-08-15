# Upload to PyPI Live
# sudo python3 setup.py sdist bdist_wheel
# sudo python3 -m twine upload dist/*

import setuptools

VERSION = "0.0.2"
NAME = "roonapi"
INSTALL_REQUIRES = ["websocket-client"]

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=NAME,
    version=VERSION,
    author='Marcel van der Veldt',
    author_email='marcelveldt@users.noreply.github.com',
    description='Provides a python interface to interact with Roon',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url = 'https://github.com/marcelveldt/python-roon.git',
    packages=['roon'],
    classifiers=(
        "Programming Language :: Python :: 2",
        "Operating System :: OS Independent",
    ),
    package_data = {'': ['.soodmsg'] },
    install_requires=INSTALL_REQUIRES,
    )