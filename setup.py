# Used this guide to create module
# http://peterdowns.com/posts/first-time-with-pypi.html

# git tag 0.1 -m "0.1 release"
# git push --tags origin master
#
# Upload to PyPI Live
# python setup.py register -r pypi
# python setup.py sdist upload -r pypi

VERSION = "0.0.1"
NAME = "roonapi"
INSTALL_REQUIRES = ["websocket-client"]

from distutils.core import setup
setup(
    name=NAME,
    packages=['roon'],
    version=VERSION,
    description='Provides a python interface to interact with Roon',
    long_description=open("README.md").read(),
    author='Marcel van der Veldt',
    author_email='marcelveldt@users.noreply.github.com',
    url='https://github.com/marcelveldt/python-roon',
    download_url = 'https://github.com/marcelveldt/python-roon.git',
    keywords= ['roon', 'roon labs', 'roon python', 'roon api'],
    classifiers = [],
    package_data = {'': ['.soodmsg'] },
    install_requires=INSTALL_REQUIRES,
    )
