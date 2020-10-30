#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" some basic functions to test on the roon api"""

import logging
import os.path
import signal
import sys
import time

from roonapi import RoonApi

token = None
if os.path.isfile("roontoken.txt"):
    with open("roontoken.txt") as f:
        token = f.read()

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "pavoni",
    "email": "my@email.com",
}

host = "192.168.1.160"


LOGGER = logging.getLogger("roonapi")

LOGGER.setLevel(logging.DEBUG)
# initialize Roon api and register the callback for state changes
roonapi = RoonApi(appinfo, token, host)

# callback will be called when we register for state events
def state_callback(event, changed_items):
    print("%s: %s" % (event, changed_items))


def source_callback(control_key, new_state):
    print(
        "source_callback --> control_key: %s - new_state: %s" % (control_key, new_state)
    )
    # just echo back the new value to set it
    publish_state = "selected" if new_state == "convenience_switch" else "standby"
    print("publish %s to source_control %s" % (publish_state, control_key))
    roonapi.update_source_control(control_key, publish_state)


def volume_callback(control_key, event, data):
    print(
        "source_callback --> control_key: %s - event: %s - data: %s"
        % (control_key, event, data)
    )
    # just echo back the new value to set it
    if event == "set_mute":
        roonapi.update_volume_control(control_key, mute=data)
    elif event == "set_volume":
        roonapi.update_volume_control(control_key, volume=data)


roonapi.register_source_control("test", "test", source_callback)
roonapi.register_volume_control("test", "test", volume_callback)


# cleanup handler to properly close the connection and save the token for later use
def cleanup(signum, frame):
    roonapi.stop()
    token = roonapi.token
    print("token: %s" % token)
    if token:
        with open("roontoken.txt", "w") as f:
            f.write(token)
    sys.exit(signum)


# signal handler
for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
    signal.signal(sig, cleanup)

# keep it alive!
while True:
    time.sleep(1)
