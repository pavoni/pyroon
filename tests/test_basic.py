#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Some basic functions to test the roon api."""

import os.path

from roonapi import RoonApi


def test_basic():

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

    with RoonApi(appinfo, token, host, port, True) as roonapi:

        # Test basic zone fetching
        zones = [zone["display_name"] for zone in roonapi.zones.values()]
        zones.sort()
        assert len(zones) == 7
        assert zones == [
            "95 Office",
            "Bedroom",
            "Hi Fi",
            "Kitchen",
            "Shower",
            "Study",
            "Tuner",
        ]

        # Test basic output fetching
        output_count = len(roonapi.outputs)
        assert output_count == 8

        token = roonapi.token
        roonapi.stop()
