#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' some basic functions to test on the roon api'''

import os.path
import signal
import sys 
import time
from roon import RoonApi   


token = None
if os.path.isfile("roontoken.txt"):
    with open("roontoken.txt") as f:
        token = f.read()
appinfo = {
        "extension_id": "python_roon_test",
        "display_name": "Python library for Roon",
        "display_version": "1.0.0",
        "publisher": "marcelveldt",
        "email": "m.vanderveldt@outlook.com"
    }

def state_callback(event, changed_items):
    printo("%s: %s" %(event, changed_items))

roonapi = RoonApi(appinfo, token)
roonapi.register_state_callback(state_callback, event_filter="zones_changed", id_filter="zolder")

def cleanup(signum, frame):
    roonapi.stop()
    with open("roontoken.txt", "w") as f:
        f.write(token)
    sys.exit(signum)
for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, cleanup)

# keep it alive!
while True:
    time.sleep(1)