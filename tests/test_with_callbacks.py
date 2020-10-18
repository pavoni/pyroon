#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' some basic functions to test on the roon api'''

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
        "publisher": "marcelveldt",
        "email": "my@email.com"
    }

# callback will be called when we register for state events
def state_callback(event, changed_items):
    print("%s: %s" %(event, changed_items))

# initialize Roon api and register the callback for state changes
roonapi = RoonApi(appinfo, token)
roonapi.register_state_callback(state_callback)

time.sleep(5)
# list all zones
print(" ###### zones ######")
for zone in roonapi.zones.values():
    print(zone["display_name"])

# list all outputs
print("###### outputs ########")
for output in roonapi.outputs.values():
    print(output)


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