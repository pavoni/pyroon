#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Some basic functions to test the roon api."""

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

# with RoonApi(appinfo, token, host, blocking_init=True) as roonapi:
with RoonApi(appinfo, token, None, blocking_init=True) as roonapi:

    # Test basic zone fetching
    zones = [zone["display_name"] for zone in roonapi.zones.values()]
    zones.sort()
    assert len(zones) == 6
    assert zones == [
        "Bedroom",
        "Hi Fi",
        "Kitchen",
        "Mixing Speakers",
        "Shower",
        "Study",
    ]

    # Test basic output fetching
    output_count = len(roonapi.outputs)
    assert output_count == 6

    # Test basic browsing
    result = roonapi.browse_by_path([])
    assert list(result) == ["items", "offset", "list"]

    headers = [item["title"] for item in result["items"]]

    assert "Library" in headers
    assert "Playlists" in headers
    assert "Internet Radio" in headers
    assert "Genres" in headers
    assert "Settings" in headers

    # print(" ###### main menu browse ######")
    # # items at first level (mainmenu items)
    # result = roonapi.browse_by_path([])
    # print([item["title"] for item in result["items"]])

    # print(" ###### search artist ######")
    # result = roonapi.browse_by_path(["Library", "Search", "Artists"], search_input="ABBA")
    # print([item["title"] for item in result["items"]])

    # print(" ###### genres ######")
    # result = roonapi.genres()
    # print([item["title"] for item in result["items"]])

    # print(" ###### subgenres ######")
    # result = roonapi.genres("Pop/Rock")
    # print([item["title"] for item in result["items"]])

    # print(" ###### zones ######")
    # for zone in roonapi.zones.values():
    #     print(zone["display_name"])

    # print(" ###### playlists ######")
    # items = roonapi.playlists()
    # print("number of playlists: %s" % items["list"]["count"])

    # print(" ###### artists ######")
    # items = roonapi.artists()
    # print("number of artists: %s" % items["list"]["count"])

    # print(" ###### albums ######")
    # items = roonapi.albums()
    # print("number of albums: %s" % items["list"]["count"])

    # print(" ###### tracks ######")
    # items = roonapi.tracks(offset=200)
    # print("number of tracks: %s" % items["list"]["count"])

    # # play playlist by name
    # zone_id = roonapi.zone_by_output_name("milo")["zone_id"]
    # output_id = roonapi.output_by_name("milo")["output_id"]
    # roonapi.play_playlist(zone_id, "Kids")

    # # some playback controls
    # time.sleep(5)
    # roonapi.playback_control(zone_id, "pause")
    # time.sleep(2)
    # roonapi.playback_control(zone_id, "play")
    # time.sleep(2)
    # roonapi.change_volume(output_id, 60)
    # time.sleep(2)
    # roonapi.change_volume(output_id, 40)

    # # play genre
    # roonapi.play_genre(zone_id, "Pop/Rock")

    # save token
    token = roonapi.token
    roonapi.stop()

print("Saving token: %s" % token)
with open("roon_test_token.txt", "w") as f:
    f.write(token)
