# python-roon
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
