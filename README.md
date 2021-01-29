# python-roon ![Build status](https://github.com/pavoni/pyroon/workflows/Build/badge.svg) ![PyPi version](https://img.shields.io/pypi/v/roonapi) ![PyPi downloads](https://img.shields.io/pypi/dm/roonapi)
python library to interface with the Roon API (www.roonlabs.com)

Full documentation will follow asap
See the tests folder for some more code examples.


Some example code:

```
from roonapi import RoonApi
appinfo = {
        "extension_id": "python_roon_test",
        "display_name": "Python library for Roon",
        "display_version": "1.0.0",
        "publisher": "marcelveldt",
        "email": "mygreat@emailaddress.com"
    }

# host can be None if you want to use discovery - but this sometimes returns the local machine, not the real roon server
host = "192.168.1.x"

# Can be None if you don't yet have a token
token = open('mytokenfile').read()

roonapi = RoonApi(appinfo, token)

# get all zones (as dict)
print(roonapi.zones)

# get all outputs (as dict)
print(roonapi.outputs)

# receive state updates in your callback
roonapi.register_state_callback(my_state_callback)


# save the token for next time
with open('mytokenfile', 'w') as f:
    f.write(roonapi.token)
