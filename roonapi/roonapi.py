from __future__ import unicode_literals

import os
import threading
import time

from .constants import (
    LOGGER,
    PAGE_SIZE,
    SERVICE_BROWSE,
    SERVICE_REGISTRY,
    SERVICE_TRANSPORT,
)
from .discovery import RoonDiscovery
from .roonapisocket import RoonApiWebSocket


def split_media_path(path):
    """Split a path (eg path/to/media) into a list for use by play_media."""

    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break

        if parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break

        path = parts[0]
        allparts.insert(0, parts[1])
    return allparts


class RoonApi:  # pylint: disable=too-many-instance-attributes
    """Class to handle talking to the roon server."""

    _roonsocket = None
    _roondiscovery = None
    _host = None
    _core_id = None
    _core_name = None

    _port = None
    _token = None
    _exit = False
    _zones = {}
    _outputs = {}
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
    def core_id(self):
        """Return the roon host."""
        return self._core_id

    @property
    def core_name(self):
        """Return the roon core name."""
        return self._core_name

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

    def is_grouped(self, output_id):
        """
        Whether this output is part of a group.

        params:
            output_id: the id of the output
        returns: boolean whether this outout is grouped
        """

        output = self.outputs[output_id]
        zone_id = output["zone_id"]
        is_grouped = len(self.zones[zone_id]["outputs"]) > 1
        return is_grouped

    def is_group_main(self, output_id):
        """
        Whether this output is the the main output of a group.

        params:
            output_id: the id of the output
        returns: boolean whether this output is the main output of a group
        """

        if not self.is_grouped(output_id):
            return False

        output = self.outputs[output_id]
        zone_id = output["zone_id"]
        is_group_main = self.zones[zone_id]["outputs"][0]["output_id"] == output_id
        return is_group_main

    def group_main_zone(self, output_id):
        """
        Get the main zone of the specified output group.

        params:
            output_id: the id of the output
        returns: the main zone this one is grouped with
        """

        if not self.is_grouped(output_id):
            return None
        output = self.outputs[output_id]
        zone_id = output["zone_id"]
        group_main_zone = self.zones[zone_id]["outputs"][0]["zone_id"]
        return group_main_zone

    def group_main_zone_name(self, output_id):
        """
        Get the name of the main zone of the specified output group.

        Note that this returns the 'raw' zone name - not the name of the group zone.

        params:
            output_id: the id of the output
        returns: name of the main zone of this group
        """

        group_main_zone = self.group_main_zone(output_id)
        if group_main_zone is None:
            return ""
        group_main_zone_name = self.zones[group_main_zone]["outputs"][0]["display_name"]
        return group_main_zone_name

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

    def pause_all(self):
        """Pause all zones."""
        return self._request(SERVICE_TRANSPORT + "/pause_all")

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
        Complex browse call on the roon api.

        reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        """
        return self._request(SERVICE_BROWSE + "/browse", opts)

    def browse_load(self, opts):
        """
        Complex browse call on the roon api.

        reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        """
        return self._request(SERVICE_BROWSE + "/load", opts)

    def play_media(self, zone_or_output_id, path, action=None):
        """
        Play the media specified.

        params:
            zone_or_output_id: where to play the media
            path: a list allowing roon to find the media
                  eg ["Library", "Artists", "Neil Young", "Harvest"] or ["My Live Radio", "BBC Radio 4"]
            action: the roon action to take to play the media - leave blank to choose the roon default
                    eg "Play Now", "Queue" or "Start Radio"
        """

        opts = {
            "zone_or_output_id": zone_or_output_id,
            "hierarchy": "browse",
            "count": PAGE_SIZE,
            "pop_all": True,
        }

        total_count = self.browse_browse(opts)["list"]["count"]
        del opts["pop_all"]

        load_opts = {
            "zone_or_output_id": zone_or_output_id,
            "hierarchy": "browse",
            "count": PAGE_SIZE,
            "offset": 0,
        }
        items = []
        for element in path:
            load_opts["offset"] = 0
            found = None
            searched = 0

            LOGGER.debug("Looking for %s", element)
            while searched < total_count and found is None:
                items = self.browse_load(load_opts)["items"]

                for item in items:
                    searched += 1
                    if item["title"] == element:
                        found = item
                        break

                load_opts["offset"] += PAGE_SIZE
            if searched >= total_count and found is None:
                LOGGER.error(
                    "Could not find media path element '%s' in %s",
                    element,
                    [item["title"] for item in items],
                )
                return None

            opts["item_key"] = found["item_key"]
            load_opts["item_key"] = found["item_key"]

            total_count = self.browse_browse(opts)["list"]["count"]

            load_opts["offset"] = 0
            items = self.browse_load(load_opts)["items"]

            if found["hint"] == "action":
                # Loading item we found already started playing
                return True

        # First item shoule be the action_list for playing this item (eg Play Genre, Play Artist, Play Album)
        if items[0]["hint"] != "action_list":
            LOGGER.error(
                "Found media does not have playable action list'%s'",
                [item["title"] for item in items],
            )
            return False

        opts["item_key"] = items[0]["item_key"]
        load_opts["item_key"] = items[0]["item_key"]
        play_header = items[0]["title"]
        self.browse_browse(opts)
        items = self.browse_load(load_opts)["items"]

        # We should now have play actions (eg Play Now, Add Next, Queue action, Start Radio)
        # So pick the one to use - the default is the first one
        if action is None:
            take_action = items[0]
        else:
            found_actions = [item for item in items if item["title"] == action]
            if len(found_actions) == 0:
                LOGGER.error(
                    "Could not find play action '%s' in %s",
                    action,
                    [item["title"] for item in items],
                )
                return False
            take_action = found_actions[0]

        if take_action["hint"] != "action":
            LOGGER.error("Found media does not have playable action'%s'")
            return False

        opts["item_key"] = take_action["item_key"]
        load_opts["item_key"] = take_action["item_key"]
        LOGGER.info("Play action was '%s' / '%s'", play_header, take_action["title"])
        self.browse_browse(opts)
        return True

    # pylint: disable=too-many-return-statements
    def play_id(self, zone_or_output_id, media_id):
        """Play based on the media_id from the browse api."""
        opts = {
            "zone_or_output_id": zone_or_output_id,
            "item_key": media_id,
            "hierarchy": "browse",
        }
        header_result = self.browse_browse(opts)
        # For Radio the above load starts play - so catch this and return
        try:
            if header_result["list"]["level"] == 0:
                LOGGER.info("Initial load started playback")
                return True
        except (NameError, KeyError, TypeError):
            LOGGER.error("Could not play id:%s, result: %s", media_id, header_result)
            return False

        if header_result is None:
            LOGGER.error(
                "Playback requested of unsupported id: %s",
                media_id,
            )
            return False

        result = self.browse_load(opts)

        first_item = result["items"][0]
        hint = first_item["hint"]
        if not (hint in ["action", "action_list"]):
            LOGGER.error(
                "Playback requested but item is a list, not a playable action or action_list id: %s",
                media_id,
            )
            return False

        if hint == "action_list":
            opts["item_key"] = first_item["item_key"]
            result = self.browse_browse(opts)
            if result is None:
                LOGGER.error(
                    "Playback requested of unsupported id: %s",
                    media_id,
                )
                return False
            result = self.browse_load(opts)
            first_item = result["items"][0]
            hint = first_item["hint"]

        if hint != "action":
            LOGGER.error(
                "Playback requested but item does not have a playable action id: %s, %s",
                media_id,
                header_result,
            )
            return False

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
            return False

        return True

    # private methods
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        appinfo,
        token=None,
        host=None,
        port=9100,
        blocking_init=True,
        core_id=None,
    ):
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
            self._roondiscovery = RoonDiscovery(self._server_discovered, core_id)
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
        LOGGER.info("Registered to Roon server %s", reginfo["display_name"])
        LOGGER.debug(reginfo)
        self._token = reginfo["token"]
        self._core_id = reginfo["core_id"]
        self._core_name = reginfo["display_name"]

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
