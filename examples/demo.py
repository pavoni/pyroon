from roonapi import RoonApi

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

# Can be None if you don't yet have a token
token = open("mytokenfile").read()

# Take a look at examples/discovery if you want to use discovery.
server = "192.168.1.160"

roonapi = RoonApi(appinfo, token, server)

# get all zones (as dict)
print(roonapi.zones)

# get all outputs (as dict)
print(roonapi.outputs)

# save the token for next time
with open("mytokenfile", "w") as f:
    f.write(roonapi.token)
