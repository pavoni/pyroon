#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Init and test discovery to test the roon api."""

import os.path

from roonapi import RoonApi, RoonDiscovery


appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "pavoni",
    "email": "my@email.com",
}


def test_discovery():
    try:
        core_id = open("my_core_id_file").read()
        token = open("my_token_file").read()
    except OSError:
        print("Please authorise first using discovery.py")
        exit()

    discover = RoonDiscovery(core_id)
    server = discover.first()
    discover.stop()

    assert server[0] != None
    assert server[1] != None

    with RoonApi(appinfo, token, server[0], server[1], True) as roonapi:
        token = roonapi.token
        roonapi.stop()

    with open("test_core_server_file", "w") as f:
        f.write(server[0])
    with open("test_core_port_file", "w") as f:
        f.write(server[1])
    with open("test_token_file", "w") as f:
        f.write(roonapi.token)
