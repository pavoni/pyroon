import time

from roonapi import RoonApi, RoonDiscovery

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

try:
    core_id = open("my_core_id_file").read()
    token = open("my_token_file").read()
except OSError:
    print("Please authorise first using discovery.py")
    exit()

discover = RoonDiscovery(core_id)
server = discover.first()
discover.stop()

roonapi = RoonApi(appinfo, token, server[0], server[1], True)


def my_state_callback(event, changed_ids):
    """Call when something changes in roon."""
    print("my_state_callback event:%s changed_ids: %s" % (event, changed_ids))
    for zone_id in changed_ids:
        zone = roonapi.zones[zone_id]
        print("zone_id:%s zone_info: %s" % (zone_id, zone))


# receive state updates in your callback
roonapi.register_state_callback(my_state_callback)

time.sleep(10)
