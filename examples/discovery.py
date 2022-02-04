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

print("Shutdown discovery")
discover.stop()

print("Found the following servers")
print(servers)
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

print("Shutdown apis")
for api in apis:
    api.stop()

# This is what we need to reconnect
core_id = api.core_id
token = api.token

print("Find authorised server via discovery")
discover = RoonDiscovery(core_id)
server = discover.first()
discover.stop()

roonapi = RoonApi(appinfo, token, server[0], server[1], True, core_id)
print(api.host)
print(api.core_name)
print(api.core_id)
print("Call the API")
print(roonapi.zones)
