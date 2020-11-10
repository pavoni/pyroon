import time

from roonapi import RoonApi, RoonDiscovery

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

discover = RoonDiscovery(None)
servers = discover.all()
apis = [RoonApi(appinfo, None, server[0], server[1], False) for server in servers]

auth_api = []
while len(auth_api) == 0:
    print("Waiting for authorisation")
    time.sleep(1)
    auth_api = [api for api in apis if api.token is not None]

api = auth_api[0]

print("Got authorisation")
print(api.host)
print(api.core_name)
print(api.core_id)

# This is what we need to reconnect
core_id = api.core_id
token = api.token

print("Shutdown discovery")
discover.stop()
for api in apis:
    api.stop()

print("Find authorised server via discovery")
discover_with_core = RoonDiscovery(None, core_id)
server = discover_with_core.first()
roonapi = RoonApi(appinfo, token, server[0], server[1], True)

print("Call the API")
print(roonapi.zones)
