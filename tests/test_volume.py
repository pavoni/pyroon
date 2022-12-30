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


def test_get_volume_db(roon_api):
    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_volume_info = db_zone["outputs"][0]["volume"]
    db_zone_output_id = db_zone["outputs"][0]["output_id"]
    roon_api.change_volume_raw(db_zone_output_id, -80)
    assert roon_api.get_volume_percent(db_zone_output_id) == 0

    roon_api.change_volume_raw(db_zone_output_id, 0)
    assert roon_api.get_volume_percent(db_zone_output_id) == 100

    roon_api.change_volume_raw(db_zone_output_id, -40)
    assert roon_api.get_volume_percent(db_zone_output_id) == 50


def test_get_volume_perent(roon_api):
    percent_zone = [
        zone
        for zone in roon_api.zones.values()
        if zone["display_name"] == "Gregs Mac System"
    ][0]

    percent_zone_volume_info = percent_zone["outputs"][0]["volume"]
    percent_zone_output_id = percent_zone["outputs"][0]["output_id"]
    roon_api.change_volume_raw(percent_zone_output_id, 0)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 0

    roon_api.change_volume_raw(percent_zone_output_id, 100)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 100

    roon_api.change_volume_raw(percent_zone_output_id, 50)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 50


def test_set_volume_db(roon_api):
    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_volume_info = db_zone["outputs"][0]["volume"]
    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    roon_api.set_volume_percent(db_zone_output_id, 0)
    assert roon_api.get_volume_percent(db_zone_output_id) == 0

    roon_api.set_volume_percent(db_zone_output_id, 100)
    assert roon_api.get_volume_percent(db_zone_output_id) == 100

    roon_api.set_volume_percent(db_zone_output_id, 50)
    assert roon_api.get_volume_percent(db_zone_output_id) == 50


def test_set_volume_percent(roon_api):
    percent_zone = [
        zone
        for zone in roon_api.zones.values()
        if zone["display_name"] == "Gregs Mac System"
    ][0]

    percent_zone_volume_info = percent_zone["outputs"][0]["volume"]
    percent_zone_output_id = percent_zone["outputs"][0]["output_id"]

    roon_api.set_volume_percent(percent_zone_output_id, 0)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 0

    roon_api.set_volume_percent(percent_zone_output_id, 100)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 100

    roon_api.set_volume_percent(percent_zone_output_id, 50)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 50


def test_change_volume_db(roon_api):
    db_zone = [
        zone for zone in roon_api.zones.values() if zone["display_name"] == "95 Office"
    ][0]

    db_zone_volume_info = db_zone["outputs"][0]["volume"]
    db_zone_output_id = db_zone["outputs"][0]["output_id"]

    roon_api.set_volume_percent(db_zone_output_id, 40)
    assert roon_api.get_volume_percent(db_zone_output_id) == 40

    roon_api.change_volume_percent(db_zone_output_id, 1)
    assert roon_api.get_volume_percent(db_zone_output_id) == 41

    roon_api.change_volume_percent(db_zone_output_id, -2)
    assert roon_api.get_volume_percent(db_zone_output_id) == 39


def test_change_volume_percent(roon_api):
    percent_zone = [
        zone
        for zone in roon_api.zones.values()
        if zone["display_name"] == "Gregs Mac System"
    ][0]

    percent_zone_volume_info = percent_zone["outputs"][0]["volume"]
    percent_zone_output_id = percent_zone["outputs"][0]["output_id"]

    roon_api.set_volume_percent(percent_zone_output_id, 40)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 40

    roon_api.change_volume_percent(percent_zone_output_id, 1)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 41

    roon_api.change_volume_percent(percent_zone_output_id, -2)
    assert roon_api.get_volume_percent(percent_zone_output_id) == 39
