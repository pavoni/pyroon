import time

from roonapi import RoonApi, RoonDiscovery

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

# The Roon output you want this code to control
VOLUME_OUTPUT = "Hi Fi"

# After running go to roon - and change the volume control method to
# Python Library for Roon
# You will then get callbacks below when the volumes for that endpoint are changed

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


def volume_control_callback(control_key, event, value):
    """Handle roon callback when Called by roon when volume is changed."""

    print(
        "volume_control_callback control_key: %s event: %s value: %s"
        % (control_key, event, value)
    )
    if event == "set_volume":
        roonapi.update_volume_control(control_key, value)
    elif event == "set_mute":
        roonapi.update_volume_control(control_key, None, value)


roonapi.register_volume_control(
    "1", VOLUME_OUTPUT, volume_control_callback, -50, "db", 2, -100, 0, True
)

time.sleep(100)
