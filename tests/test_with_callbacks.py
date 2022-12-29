#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Some simple tests for callback on the roon api."""

import os.path

from roonapi import RoonApi, LOGGER


def test_callbacks():
    callback_count = 0
    events = []

    try:
        host = open("test_core_server_file").read()
        port = open("test_core_port_file").read()
        token = open("my_token_file").read()
    except OSError:
        print("Please authorise first using discovery.py")
        exit()

    appinfo = {
        "extension_id": "python_roon_test",
        "display_name": "Python library for Roon",
        "display_version": "1.0.0",
        "publisher": "pavoni",
        "email": "my@email.com",
    }

    # initialize Roon api and register the callback for state changes
    with RoonApi(appinfo, token, host, port, True) as roonapi:

        def state_callback(event, changed_items):
            """Update details when the roon state changes."""
            nonlocal callback_count, events
            callback_count += 1
            events.append(event)
            LOGGER.info("%s: %s", event, changed_items)

        roonapi.register_state_callback(state_callback)

        zones = [
            zone
            for zone in roonapi.zones.values()
            if zone["display_name"] == "95 Office"
        ]

        assert len(zones) == 1

        test_zone = zones[0]
        test_output_id = test_zone["outputs"][0]["output_id"]

        assert callback_count == 0
        assert events == []

        roonapi.change_volume(test_output_id, 1, method="relative")
        assert callback_count == 2
        assert events == ["zones_changed", "outputs_changed"]

        events = []

        roonapi.change_volume(test_output_id, -1, method="relative")
        assert callback_count == 4
        assert events == ["zones_changed", "outputs_changed"]

        roonapi.stop()
        token = roonapi.token
