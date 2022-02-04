import time

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
host = "192.168.3.61"
port = 9330

roonapi = RoonApi(appinfo, token, host, port)


def my_state_callback(event, changed_ids):
    """Call when something changes in roon."""
    print("my_state_callback event:%s changed_ids: %s" % (event, changed_ids))
    for zone_id in changed_ids:
        zone = roonapi.zones[zone_id]
        print("zone_id:%s zone_info: %s" % (zone_id, zone))


# receive state updates in your callback
roonapi.register_state_callback(my_state_callback)

time.sleep(10)

# save the token for next time
with open("mytokenfile", "w") as f:
    f.write(roonapi.token)
