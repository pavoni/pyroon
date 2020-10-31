from __future__ import unicode_literals

import threading
import time

from .constants import (
    LOGGER,
    SERVICE_BROWSE,
    SERVICE_REGISTRY,
    SERVICE_TRANSPORT,
)
from .discovery import RoonDiscovery
from .roonapisocket import RoonApiWebSocket


class RoonApi:  # pylint: disable=too-many-instance-attributes
    """Class to handle talking to the roon server."""

    _roonsocket = None
    _roondiscovery = None
    _host = None
    _port = None
    _token = None
    _exit = False
    _zones = {}
    _outputs = {}
    _source_controls_request_id = None
    _volume_controls_request_id = None
    _source_controls = {}
    _volume_controls = {}
    _state_callbacks = []
    ready = False

    @property
    def token(self):
        """Return the authentication key from the registration with Roon."""
        return self._token

    @property
    def host(self):
        """Return the roon host."""
        return self._host

    @property
    def zones(self):
        """Return All zones as a dict."""
        return self._zones

    @property
    def outputs(self):
        """All outputs, returned as dict."""
        return self._outputs

    def zone_by_name(self, zone_name):
        """Get zone details by name."""
        for zone in self.zones.values():
            if zone["display_name"] == zone_name:
                return zone
        return None

    def output_by_name(self, output_name):
        """Get the output details from the name."""
        for output in self.outputs.values():
            if output["display_name"] == output_name:
                return output
        return None

    def zone_by_output_id(self, output_id):
        """Get the zone details by output id."""
        for zone in self.zones.values():
            for output in zone["outputs"]:
                if output["output_id"] == output_id:
                    return zone
        return None

    def zone_by_output_name(self, output_name):
        """
        Get the zone details by an output name.

        params:
            output_name: the name of the output
        returns: full zone details (dict)
        """

        for zone in self.zones.values():
            for output in zone["outputs"]:
                if output["display_name"] == output_name:
                    return zone
        return None

    def get_image(self, image_key, scale="fit", width=500, height=500):
        """
        Get the image url for the specified image key.

        params:
            image_key: the key for the image as retrieved in other api calls
            scale: optional (value of fit, fill or stretch)
            width: the width of the image (required if scale is specified)
            height: the height of the image (required if scale is set)
        returns: string with the full url to the image
        """
        return "http://%s:%s/api/image/%s?scale=%s&width=%s&height=%s" % (
            self._host,
            self._port,
            image_key,
            scale,
            width,
            height,
        )

    def playback_control(self, zone_or_output_id, control="play"):
        """
        Send player command to the specified zone.

        params:
            zone_or_output_id: the id of the zone or output
            control:
                 * "play" - If paused or stopped, start playback
                 * "pause" - If playing or loading, pause playback
                 * "playpause" - If paused or stopped, start playback.
                                 If playing or loading, pause playback.
                 * "stop" - Stop playback and release the audio device immediately
                 * "previous" - Go to the start of the current track, or to the previous track
                 * "next" - Advance to the next track
        """
        data = {"zone_or_output_id": zone_or_output_id, "control": control}
        return self._request(SERVICE_TRANSPORT + "/control", data)

    def standby(self, output_id, control_key=None):
        """
        Send standby command to the specified output.

        params:
            output_id: the id of the output to put in standby
            control_key: The control_key that identifies the source_control
                         that is to be put into standby. If omitted,
                         then all source controls on this output that support
                         standby will be put into standby.
        """
        data = {"output_id": output_id, "control_key": control_key}
        return self._request(SERVICE_TRANSPORT + "/standby", data)

    def convenience_switch(self, output_id, control_key=None):
        """
        Switch (convenience) an output, take it out of standby if needed.

        params:
            output_id: the id of the output that should be convenience-switched.
            control_key: The control_key that identifies the source_control that is to be switched.
                         If omitted, then all controls on this output will be convenience switched.
        """
        data = {"output_id": output_id, "control_key": control_key}
        return self._request(SERVICE_TRANSPORT + "/convenience_switch", data)

    def mute(self, output_id, mute=True):
        """
        Mute/unmute an output.

        params:
            output_id: the id of the output that should be muted/unmuted
            mute: bool if the output should be muted. Will unmute if set to False
        """
        how = "mute" if mute else "unmute"
        data = {"output_id": output_id, "how": how}
        return self._request(SERVICE_TRANSPORT + "/mute", data)

    def change_volume(self, output_id, value, method="absolute"):
        """
        Change the volume of an output.

        For convenience you can always just give the new volume level as percentage.

        params:
            output_id: the id of the output
            value: The new volume value, or the increment value or step (as percentage)
            method: How to interpret the volume ('absolute'|'relative'|'relative_step')
        """
        if "volume" not in self._outputs[output_id]:
            LOGGER.info("This endpoint has fixed volume.")
            return None
        # Home assistant was catching this - so catch here
        # to try and diagnose what needs to be checked.
        try:
            if method == "absolute":
                if self._outputs[output_id]["volume"]["type"] == "db":
                    value = int((float(value) / 100) * 80) - 80
            data = {"output_id": output_id, "how": method, "value": value}
            return self._request(SERVICE_TRANSPORT + "/change_volume", data)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("set_volume_level failed for entity %s.", str(exc))
            return None

    def seek(self, zone_or_output_id, seconds, method="absolute"):
        """
        Seek to a time position within the now playing media.

        params:
            zone_or_output_id: the id of the zone or output
            seconds: The target seek position
            method: How to interpret the target seek position ('absolute'|'relative')
        """
        data = {
            "zone_or_output_id": zone_or_output_id,
            "how": method,
            "seconds": seconds,
        }
        return self._request(SERVICE_TRANSPORT + "/seek", data)

    def shuffle(self, zone_or_output_id, shuffle=True):
        """
        Enable or disable playing in random order.

        params:
            zone_or_output_id: the id of the output or zone
            shuffle: bool if shuffle should be enabled. False will disable shuffle
        """
        data = {"zone_or_output_id": zone_or_output_id, "shuffle": shuffle}
        return self._request(SERVICE_TRANSPORT + "/change_settings", data)

    def repeat(self, zone_or_output_id, repeat=True):
        """
        Enable/disable playing in a loop.

        params:
            zone_or_output_id: the id of the output or zone
            repeat: bool if repeat should be enabled. False will disable shuffle
        """
        loop = "loop" if repeat else "disabled"
        data = {"zone_or_output_id": zone_or_output_id, "loop": loop}
        return self._request(SERVICE_TRANSPORT + "/change_settings", data)

    def transfer_zone(self, from_zone_or_output_id, to_zone_or_output_id):
        """
        Transfer the current queue from one zone to another.

        params:
            from_zone_or_output_id - The source zone or output
            to_zone_or_output_id - The destination zone or output
        """
        data = {
            "from_zone_or_output_id": from_zone_or_output_id,
            "to_zone_or_output_id": to_zone_or_output_id,
        }
        return self._request(SERVICE_TRANSPORT + "/transfer_zone", data)

    def group_outputs(self, output_ids):
        """
        Create a group of synchronized audio outputs.

        params:
            output_ids - The outputs to group. The first output's zone's queue is preserved.
        """
        data = {"output_ids": output_ids}
        return self._request(SERVICE_TRANSPORT + "/group_outputs", data)

    def ungroup_outputs(self, output_ids):
        """
        Ungroup outputs previous grouped.

        params:
            output_ids - The outputs to ungroup.
        """
        data = {"output_ids": output_ids}
        return self._request(SERVICE_TRANSPORT + "/ungroup_outputs", data)

    # pylint: disable=too-many-arguments
    def register_source_control(
        self,
        control_key,
        display_name,
        callback,
        initial_state="selected",
        supports_standby=True,
    ):
        """Register a new source control on the api."""
        if control_key in self._source_controls:
            LOGGER.error("source_control %s is already registered!" % control_key)
            return
        control_data = {
            "display_name": display_name,
            "supports_standby": supports_standby,
            "status": initial_state,
            "control_key": control_key,
        }
        self._source_controls[control_key] = (callback, control_data)
        if self._source_controls_request_id:
            data = {"controls_added": [control_data]}
            self._roonsocket.send_continue(self._source_controls_request_id, data)

    def update_source_control(self, control_key, new_state):
        """Update an existing source control on the api."""
        if control_key not in self._source_controls:
            LOGGER.warning("source_control %s is not (yet) registered!" % control_key)
            return
        if not self._source_controls_request_id:
            LOGGER.warning("Not yet registered, can not update source control")
            return
        self._source_controls[control_key][1]["status"] = new_state
        data = {"controls_changed": [self._source_controls[control_key][1]]}
        self._roonsocket.send_continue(self._source_controls_request_id, data)

    def register_volume_control(
        self,
        control_key,
        display_name,
        callback,
        initial_volume=0,
        volume_type="number",
        volume_step=2,
        volume_min=0,
        volume_max=100,
        is_muted=False,
    ):
        """Register a new volume control on the api."""
        if control_key in self._volume_controls:
            LOGGER.error("source_control %s is already registered!" % control_key)
            return
        control_data = {
            "display_name": display_name,
            "volume_type": volume_type,
            "volume_min": volume_min,
            "volume_max": volume_max,
            "volume_value": initial_volume,
            "volume_step": volume_step,
            "is_muted": is_muted,
            "control_key": control_key,
        }
        self._volume_controls[control_key] = (callback, control_data)
        if self._volume_controls_request_id:
            data = {"controls_added": [control_data]}
            self._roonsocket.send_continue(self._volume_controls_request_id, data)

    def update_volume_control(self, control_key, volume=None, mute=None):
        """Update an existing volume control, report its state to Roon."""
        if control_key not in self._volume_controls:
            LOGGER.warning("volume_control %s is not (yet) registered!" % control_key)
            return
        if not self._volume_controls_request_id:
            LOGGER.warning("Not yet registered, can not update volume control")
            return
        if volume is not None:
            self._volume_controls[control_key][1]["volume_value"] = volume
        if mute is not None:
            self._volume_controls[control_key][1]["is_muted"] = mute
        data = {"controls_changed": [self._volume_controls[control_key][1]]}
        self._roonsocket.send_continue(self._volume_controls_request_id, data)

    def register_state_callback(self, callback, event_filter=None, id_filter=None):
        """
        Register a callback to be informed about changes to zones or outputs.

        params:
            callback: method to be called when state changes occur, it will be passed an event param as string and a list of changed objects
                      callback will be called with params:
                      - event: string with name of the event ("zones_changed", "zones_seek_changed", "outputs_changed")
                      - a list with the zone or output id's that changed
            event_filter: only callback if the event is in this list
            id_filter: one or more zone or output id's or names to filter on (list or string)
        """
        if not event_filter:
            event_filter = []
        elif not isinstance(event_filter, list):
            event_filter = [event_filter]
        if not id_filter:
            id_filter = []
        elif not isinstance(id_filter, list):
            id_filter = [id_filter]
        self._state_callbacks.append((callback, event_filter, id_filter))

    def register_queue_callback(self, callback, zone_or_output_id=""):
        """
        Subscribe to queue change events.

        callback: function which will be called with the updated data (provided as dict object
        zone_or_output_id: If provided, only listen for updates for this zone or output
        """
        if zone_or_output_id:
            opt_data = {"zone_or_output_id": zone_or_output_id}
        else:
            opt_data = None
        self._roonsocket.subscribe(SERVICE_TRANSPORT, "queue", callback, opt_data)

    def browse_browse(self, opts):
        """
        Undocumented and complex browse call on the roon api.

        reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        """
        return self._request(SERVICE_BROWSE + "/browse", opts)

    def browse_load(self, opts):
        """
        Undocumented and complex browse call on the roon api.

        reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        """
        return self._request(SERVICE_BROWSE + "/load", opts)

    def browse_pop_all(self, opts):
        """
        Undocumented and complex browse call on the roon api.

        reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        """
        return self._request(SERVICE_BROWSE + "/pop_all", opts)

    def browse_pop(self, opts):
        """
        Undocumented and complex browse call on the roon api.

        reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        """
        return self._request(SERVICE_BROWSE + "/pop", opts)

    def browse_by_path(
        self, search_paths, zone_or_output_id="", offset=0, search_input=None
    ):
        """
        Workaround to browse content by specifying the path to the content.

        params:
            search_paths: a list of names to look for in the hierarchie.
                          e.g. ["Playlists", "My Favourite Playlist"]
            zone_or_output_id: id of a zone or output on which behalf the search is performed.
                          can be ommitted for browsing but required for actions (play etc.)
            offset: a list will only return 100 items, to get more use the offset
        returns: a list of items (if found) as returned by the browse function
        """
        opts = {"hierarchy": "browse", "pop_all": True}
        if zone_or_output_id:
            opts["zone_or_output_id"] = zone_or_output_id
        # go to first level (home)
        result = self.browse_browse(opts)
        if not result:
            return None
        # items at first level (mainmenu items)
        result = self.browse_load(opts)
        opts["pop_all"] = False
        for search_for in search_paths:
            if not result or "items" not in result:
                break
            for item in result["items"]:
                if (
                    item["title"] == search_for
                    or search_input
                    and item.get("input_prompt")
                ):
                    opts["item_key"] = item["item_key"]
                    if item.get("input_prompt"):
                        opts["input"] = search_input
                    result = self.browse_browse(opts)
                    if result and "list" in result and result["list"]["count"] > 100:
                        opts["offset"] = offset
                        opts["set_display_offset"] = offset
                    result = self.browse_load(opts)
        return result

    def playlists(self, offset=0):
        """Return the list of playlists."""
        return self.browse_by_path(["Playlists"], offset=offset)

    def internet_radio(self, offset=0):
        """Return the list of internet radio stations."""
        return self.browse_by_path(["Internet Radio"], offset=offset)

    def artists(self, offset=0):
        """Return the list of artists in the library."""
        return self.browse_by_path(["Library", "Artists"], offset=offset)

    def albums(self, offset=0):
        """Return the list of albums in the library."""
        return self.browse_by_path(["Library", "Albums"], offset=offset)

    def tracks(self, offset=0):
        """Return the list of tracks in the library."""
        return self.browse_by_path(["Library", "Tracks"], offset=offset)

    def tags(self, offset=0):
        """Return the list of tags in the library."""
        return self.browse_by_path(["Library", "Tags"], offset=offset)

    def genres(self, subgenres_for="", offset=0):
        """Return the list of genres in the library."""
        return self.browse_by_path(["Genres", subgenres_for], offset=offset)

    def play_playlist(self, zone_or_output_id, playlist_title, shuffle=False):
        """Play playlist by name on the specified zone."""
        play_action = "Shuffle" if shuffle else "Play Now"
        return self.browse_by_path(
            ["Playlists", playlist_title, "Play Playlist", play_action],
            zone_or_output_id,
        )

    def queue_playlist(self, zone_or_output_id, playlist_title):
        """Queue playlist by name on the specified zone."""
        return self.browse_by_path(
            ["Playlists", playlist_title, "Play Playlist", "Queue"], zone_or_output_id
        )

    def play_radio(self, zone_or_output_id, radio_title):
        """Play internet radio by name on the specified zone."""
        return self.browse_by_path(
            ["Internet Radio", radio_title, "Play Radio", "Play Now"], zone_or_output_id
        )

    def play_genre(self, zone_or_output_id, genre_name, subgenre="", shuffle=False):
        """Play specified genre on the specified zone."""
        action = "Shuffle" if shuffle else "Play Genre"
        if subgenre:
            return self.browse_by_path(
                ["Genres", genre_name, subgenre, "Play Genre", action],
                zone_or_output_id,
            )
        return self.browse_by_path(
            ["Genres", genre_name, "Play Genre", action], zone_or_output_id
        )

    def play_id(self, zone_or_output_id, media_id):
        """Play based on the media_id from the browse api."""
        opts = {
            "zone_or_output_id": zone_or_output_id,
            "item_key": media_id,
            "hierarchy": "browse",
        }
        header_result = self.browse_browse(opts)
        # For Internet radio the above load starts play - so catch this and return
        try:
            if header_result["list"]["level"] == 0:
                LOGGER.info("Initial load started playback")
                return
        except NameError:
            pass

        if header_result is None:
            LOGGER.error(
                "Playback requested of unsupported id: %s",
                media_id,
            )
            return

        result = self.browse_load(opts)

        first_item = result["items"][0]
        hint = first_item["hint"]
        if not (hint in ["action", "action_list"]):
            LOGGER.error(
                "Playback requested but item is a list, not a playable action or action_list id: %s",
                media_id,
            )
            return

        if hint == "action_list":
            opts["item_key"] = first_item["item_key"]
            result = self.browse_browse(opts)
            if result is None:
                LOGGER.error(
                    "Playback requested of unsupported id: %s",
                    media_id,
                )
                return
            result = self.browse_load(opts)
            first_item = result["items"][0]
            hint = first_item["hint"]

        if hint != "action":
            LOGGER.error(
                "Playback requested but item does not have a playable action id: %s, %s",
                media_id,
                header_result,
            )
            return

        play_action = result["items"][0]
        hint = play_action["hint"]
        LOGGER.info("'%s' for '%s')", play_action["title"], header_result)
        opts["item_key"] = play_action["item_key"]
        self.browse_browse(opts)
        if result is None:
            LOGGER.error(
                "Playback requested of unsupported id: %s",
                media_id,
            )

    def search_artists(self, search_input):
        """Search for artists by name."""
        return self.browse_by_path(
            ["Library", "Search", "Artists"], search_input=search_input
        )

    # private methods

    def __init__(self, appinfo, token=None, host=None, port=9100, blocking_init=True):
        """
        Set up the connection with Roon.

        appinfo: a dict of the required information about the app that should be connected to the api
        token: used for presistant storage of the auth token, will be set to token attribute if retrieved. You should handle saving of the key yourself
        host: optional the ip or hostname of the Roon server, will be auto discovered if ommitted
        port: optional the http port of the Roon websockets api. Should be default of 9100
        blocking_init: By default the init will halt untill the socket is connected and the app is authenticated,
                       if you set bool to False the init will continue but you will only receive data once the connection is fully initialized.
                       The latter is preferred if you're (only) using the callbacks
        """
        self._appinfo = appinfo
        self._token = token
        if not appinfo or not isinstance(appinfo, dict):
            raise "appinfo missing or in incorrect format!"

        if host and port:
            self._server_discovered(host, port)
        else:
            self._roondiscovery = RoonDiscovery(self._server_discovered)
            self._roondiscovery.start()
        # block untill we're ready
        if blocking_init:
            while not self.ready and not self._exit:
                time.sleep(1)
        # start socket watcher
        thread_id = threading.Thread(target=self._socket_watcher)
        thread_id.daemon = True
        thread_id.start()

    # pylint: disable=redefined-builtin
    def __exit__(self, type, value, exc_tb):
        """Stop socket and discovery on exit."""
        self.stop()

    def __enter__(self):
        """Just return self on entry."""
        return self

    def stop(self):
        """Stop socket and discovery."""
        self._exit = True
        if self._roondiscovery:
            self._roondiscovery.stop()
        if self._roonsocket:
            self._roonsocket.stop()

    def _server_discovered(self, host, port):
        """(Auto) discovered the roon server on the network."""
        LOGGER.info("Connecting to Roon server %s:%s" % (host, port))
        ws_address = "ws://%s:%s/api" % (host, port)
        self._host = host
        self._port = port
        self._roonsocket = RoonApiWebSocket(ws_address)

        self._roonsocket.register_connected_callback(self._socket_connected)
        self._roonsocket.register_registered_calback(self._server_registered)

        self._roonsocket.start()

    def _socket_connected(self):
        """Successfully connected the websocket."""
        LOGGER.info("Connection with roon websockets (re)created.")
        self.ready = False
        self._source_controls_request_id = None
        self._volume_controls_request_id = None
        # authenticate / register
        # warning: at first launch the user has to approve the app in the Roon settings.
        appinfo = self._appinfo.copy()
        appinfo["required_services"] = [SERVICE_TRANSPORT, SERVICE_BROWSE]
        appinfo["provided_services"] = []
        if self._token:
            appinfo["token"] = self._token
        if not self._token:
            LOGGER.info("The application should be approved within Roon's settings.")
        else:
            LOGGER.info("Confirming previous registration with Roon...")
        self._roonsocket.send_request(SERVICE_REGISTRY + "/register", appinfo)

    def _server_registered(self, reginfo):
        LOGGER.info("Registered to Roon server %s" % reginfo["display_name"])
        LOGGER.debug(reginfo)
        self._token = reginfo["token"]
        # fill zones and outputs dicts one time so the data is available right away
        if not self._zones:
            self._zones = self._get_zones()
        if not self._outputs:
            self._outputs = self._get_outputs()
        # subscribe to state change events
        self._roonsocket.subscribe(SERVICE_TRANSPORT, "zones", self._on_state_change)
        self._roonsocket.subscribe(SERVICE_TRANSPORT, "outputs", self._on_state_change)
        # set flag that we're fully initialized (used for blocking init)
        self.ready = True

    # pylint: disable=too-many-branches
    def _on_state_change(self, msg):
        """Process messages we receive from the roon websocket into a more usable format."""
        events = []
        if not msg or not isinstance(msg, dict):
            return
        for state_key, state_values in msg.items():
            changed_ids = []
            filter_keys = []
            if state_key in [
                "zones_seek_changed",
                "zones_changed",
                "zones_added",
                "zones",
            ]:
                for zone in state_values:
                    if zone["zone_id"] in self._zones:
                        self._zones[zone["zone_id"]].update(zone)
                    else:
                        self._zones[zone["zone_id"]] = zone
                    changed_ids.append(zone["zone_id"])
                    if "display_name" in zone:
                        filter_keys.append(zone["display_name"])
                    if "outputs" in zone:
                        for output in zone["outputs"]:
                            filter_keys.append(output["output_id"])
                            filter_keys.append(output["display_name"])
                event = (
                    "zones_seek_changed"
                    if state_key == "zones_seek_changed"
                    else "zones_changed"
                )
                events.append((event, changed_ids, filter_keys))
            elif state_key in ["outputs_changed", "outputs_added", "outputs"]:
                for output in state_values:
                    if output["output_id"] in self._outputs:
                        self._outputs[output["output_id"]].update(output)
                    else:
                        self._outputs[output["output_id"]] = output
                    changed_ids.append(output["output_id"])
                    filter_keys.append(output["display_name"])
                    filter_keys.append(output["zone_id"])
                event = "outputs_changed"
                events.append((event, changed_ids, filter_keys))
            elif state_key == "zones_removed":
                for item in state_values:
                    del self._zones[item]
            elif state_key == "outputs_removed":
                for item in state_values:
                    del self._outputs[item]
            else:
                LOGGER.warning("unknown state change: %s" % msg)
        for event, changed_ids, filter_keys in events:
            filter_keys.extend(changed_ids)
            for item in self._state_callbacks:
                callback = item[0]
                event_filter = item[1]
                id_filter = item[2]
                if event_filter and (event not in event_filter):
                    continue
                if id_filter and set(id_filter).isdisjoint(filter_keys):
                    continue
                try:
                    callback(event, changed_ids)
                # pylint: disable=broad-except
                except Exception:
                    LOGGER.exception("Error while executing callback!")

    def _get_outputs(self):
        outputs = {}
        data = self._request(SERVICE_TRANSPORT + "/get_outputs")
        if data and "outputs" in data:
            for output in data["outputs"]:
                outputs[output["output_id"]] = output
        return outputs

    def _get_zones(self):
        zones = {}
        data = self._request(SERVICE_TRANSPORT + "/get_zones")
        if data and "zones" in data:
            for zone in data["zones"]:
                zones[zone["zone_id"]] = zone
        return zones

    def _request(self, command, data=None):
        """Send command and wait for result."""
        if not self._roonsocket:
            retries = 20
            while (not self.ready or not self._roonsocket) and retries:
                retries -= 1
                time.sleep(0.2)
            if not self.ready or not self._roonsocket:
                LOGGER.warning("socket is not yet ready")
                if not self._roonsocket:
                    return None
        request_id = self._roonsocket.send_request(command, data)
        result = None
        retries = 50
        while retries:
            result = self._roonsocket.results.get(request_id)
            if result:
                break
            retries -= 1
            time.sleep(0.05)
        try:
            del self._roonsocket.results[request_id]
        except KeyError:
            pass
        return result

    def _socket_watcher(self):
        """Monitor the connection state of the socket and reconnect if needed."""
        while not self._exit:
            if self._roonsocket and self._roonsocket.failed_state:
                LOGGER.warning("Socket connection lost! Will try to reconnect in 20s")
                count = 0
                while not self._exit and count < 21:
                    count += 1
                    time.sleep(1)
                if not self._exit:
                    self._server_discovered(self._host, self._port)
            time.sleep(2)
