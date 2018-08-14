# Used this guide to create module
# http://peterdowns.com/posts/first-time-with-pypi.html

# git tag 0.1 -m "0.1 release"
# git push --tags origin master
#
# Upload to PyPI Live
# python setup.py register -r pypi
# python setup.py sdist upload -r pypi


from distutils.core import setup
setup(
    name='roon',
    packages=['python-roon'],
    version='1.0',
    description='Provides a python interface to interact with Roon',
    author='Marcel van der Veldt',
    author_email='marcelveldt@users.noreply.github.com',
    url='https://github.com/marcelveldt/python-roon',
    download_url = 'https://github.com/mezz64/pyemby/tarball/1.5',
    keywords= ['roon', 'roon labs', 'roon python'],
    classifiers = [],
    )
