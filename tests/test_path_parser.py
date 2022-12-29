# !/usr/bin/env python
# -*- coding: utf-8 -*-

from roonapi import split_media_path

"""Some tests of the path parser"""


def test_simple_paths():

    assert split_media_path("Library/Artists/Neil Young") == [
        "Library",
        "Artists",
        "Neil Young",
    ]

    assert split_media_path("Library/Artists/Neil Young/Harvest") == [
        "Library",
        "Artists",
        "Neil Young",
        "Harvest",
    ]

    assert split_media_path("My Live Radio/BBC Radio 4") == [
        "My Live Radio",
        "BBC Radio 4",
    ]

    assert split_media_path("Genres/Jazz/Cool") == [
        "Genres",
        "Jazz",
        "Cool",
    ]

    assert split_media_path("Genres/Rock/Pop") == [
        "Genres",
        "Rock",
        "Pop",
    ]


def test_edge_cases():

    assert split_media_path("") == []

    assert split_media_path("Library") == [
        "Library",
    ]

    assert split_media_path("/") == ["", ""]


def test_quoted_paths():

    assert split_media_path('"Library"/Artists/Neil Young') == [
        "Library",
        "Artists",
        "Neil Young",
    ]

    assert split_media_path('Genres/"Rock/Pop"') == [
        "Genres",
        "Rock/Pop",
    ]

    assert split_media_path('Genres/"Rock/Pop"') == [
        "Genres",
        "Rock/Pop",
    ]
