#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" some basic functions to test on the roon api"""

import os.path

from roonapi import RoonApi

token = None
if os.path.isfile("roon_test_token.txt"):
    with open("roon_test_token.txt") as f:
        token = f.read()

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "pavoni",
    "email": "my@email.com",
}

host = "192.168.1.160"

callback_count = 0
events = []

# callback will be called when we register for state events
def state_callback(event, changed_items):
    global callback_count, events
    callback_count += 1
    events.append(event)
    print("%s: %s" % (event, changed_items))

host = "192.168.1.160"
# initialize Roon api and register the callback for state changes
roonapi = RoonApi(appinfo, token, host)
roonapi.register_state_callback(state_callback)

zones = [ zone for zone in roonapi.zones.values() if zone["display_name"] == "Mixing Speakers"]

assert len(zones) == 1

test_zone = zones[0]
test_output_id = test_zone["outputs"][0]["output_id"]

assert callback_count == 0
assert events == []

roonapi.change_volume(test_output_id, 1, method="relative")
assert callback_count == 2
assert events == ['zones_changed', 'outputs_changed']

events = []

roonapi.change_volume(test_output_id, -1, method="relative")
assert callback_count == 4
assert events == ['zones_changed', 'outputs_changed']

roonapi.stop()
token = roonapi.token
print("Saving token: %s" % token)
if token:
    with open("roon_test_token.txt", "w") as f:
        f.write(token)


