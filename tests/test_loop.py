#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Some simple tests for callback on the roon api."""

import os.path, pytest

from roonapi import RoonApi, LOGGER


@pytest.fixture()
def roon_api(request):
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

    def teardown():
        roonapi.stop()

    request.addfinalizer(teardown)

    # initialize Roon api and register the callback for state changes
    roonapi = RoonApi(appinfo, token, host, port, True)
    return roonapi


def test_loop_settings(roon_api):
    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "disabled"

    roon_api.repeat(db_zone_output_id, "loop_one")

    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "loop_one"

    roon_api.repeat(db_zone_output_id, "loop")

    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "loop"

    roon_api.repeat(db_zone_output_id, "disabled")

    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "disabled"


def test_loop_old_style_settings(roon_api):
    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "disabled"

    roon_api.repeat(db_zone_output_id, True)

    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "loop"

    roon_api.repeat(db_zone_output_id, False)

    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "disabled"

    roon_api.repeat(db_zone_output_id)

    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    loop = db_zone["settings"]["loop"]
    assert loop == "loop"

    roon_api.repeat(db_zone_output_id, False)
