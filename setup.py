# Upload to PyPI Live
# sudo python3 setup.py sdist bdist_wheel
# sudo python3 -m twine upload dist/*

from setuptools import setup, find_packages

VERSION = "0.0.22dev1"
NAME = "roonapi"
INSTALL_REQUIRES = ["websocket-client"]

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name=NAME,
    version=VERSION,
    author='Marcel van der Veldt, Greg Dowling',
    author_email='mail@gregdowling.com',
    description='Provides a python interface to interact with Roon',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url = 'http://github.com/pavoni/pyroon',
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Home Automation"],
    package_data = {'': ['.soodmsg'] },
    install_requires=INSTALL_REQUIRES,
    )