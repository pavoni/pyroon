from __future__ import unicode_literals
import time
from .constants import *
from .roonapisocket import RoonApiWebSocket
from .discovery  import RoonDiscovery


class RoonApi():
    _roonsocket = None
    _token = None
    _host = ""
    _port = 0
    _exit = False
    _zones = {}
    _outputs = {}
    _state_callbacks = []
    init_complete = False

    @property
    def token(self):
        ''' the authentication key that was retrieved from the registration with Roon'''
        return self._token
    
    @property
    def zones(self):
        ''' all zones, returned as dict'''
        return self._zones

    @property
    def outputs(self):
        ''' all outputs, returned as dict'''
        return self._outputs

    def zone_by_name(self, zone_name):
        ''' get zone details by name'''
        for zone in self.zones.values():
            if zone["display_name"] == zone_name:
                return zone
        return None

    def output_by_name(self, output_name):
        ''' get the output details from the name'''
        for output in self.outputs.values():
            if output["display_name"] == output_name:
                return output
        return None

    def zone_by_output_id(self, output_id):
        ''' get the zone details by output id'''
        for zone in self.zones.values():
            for output in zone["outputs"]:
                if output["output_id"] == output_id:
                    return zone
        return None

    def zone_by_output_name(self, output_name):
        ''' 
            get the zone details by an output name
            params:
                output_name: the name of the output
            returns: full zone details (dict)
        '''
        for zone in self.zones.values():
            for output in zone["outputs"]:
                if output["display_name"] == output_name:
                    return zone
        return None

    def get_image(self, image_key, scale="fit", width=500, height=500):
        ''' 
            get the image url for the specified image key
            params:
                image_key: the key for the image as retrieved in other api calls
                scale: optional (value of fit, fill or stretch)
                width: the width of the image (required if scale is specified)
                height: the height of the image (required if scale is set)
            returns: string with the full url to the image
        '''
        return "http://%s:%s/api/image/%s?scale=%s&width=%s&height=%s" %(self._host, self._port, image_key, scale, width, height)

    def playback_control(self, zone_or_output_id, control="play"):
        '''
            send player command to the specified zone
            params:
                zone_or_output_id: the id of the zone or output
                control:
                     * "play" - If paused or stopped, start playback
                     * "pause" - If playing or loading, pause playback
                     * "playpause" - If paused or stopped, start playback. If playing or loading, pause playback.
                     * "stop" - Stop playback and release the audio device immediately
                     * "previous" - Go to the start of the current track, or to the previous track
                     * "next" - Advance to the next track
        '''
        data = {
                   "zone_or_output_id": zone_or_output_id,
                   "control":           control
                }
        return self._request(ServiceTransport + "/control", data)

    def standby(self, output_id, control_key=None):
        '''
            send standby command to the specified output
            params:
                output_id: the id of the output to put in standby
                control_key: The control_key that identifies the source_control that is to be put into standby. 
                             If omitted, then all source controls on this output that support standby will be put into standby.
        '''
        data = {  "output_id": output_id, "control_key": control_key }
        return self._request(ServiceTransport + "/standby", data)

    def convenience_switch(self, output_id, control_key=None):
        '''
            Convenience switch an output, taking it out of standby if needed.
            params:
                output_id: the id of the output that should be convenience-switched.
                control_key: The control_key that identifies the source_control that is to be switched.
                             If omitted, then all controls on this output will be convenience switched.
        '''
        data = {  "output_id": output_id, "control_key": control_key }
        return self._request(ServiceTransport + "/convenience_switch", data)

    def mute(self, output_id, mute=True):
        '''
            Mute/unmute an output.
            params:
                output_id: the id of the output that should be muted/unmuted
                mute: bool if the output should be muted. Will unmute if set to False
        '''
        how = "mute" if mute else "unmute"
        data = {  "output_id": output_id, "how": how }
        return self._request(ServiceTransport + "/mute", data)

    def change_volume(self, output_id, value, method="absolute"):
        '''
            Change the volume of an output. For convenience you can always just give te new volume level as percentage
            params:
                output_id: the id of the output
                value: The new volume value, or the increment value or step (as percentage)
                method: How to interpret the volume ('absolute'|'relative'|'relative_step')
        '''
        if method == "absolute":
            if self._outputs[output_id]["volume"]["type"] == "db":
                value = int((float(value) / 100) * 80) - 80
        data = {  "output_id": output_id, "how": method, "value": value }
        return self._request(ServiceTransport + "/change_volume", data)

    def seek(self, zone_or_output_id, seconds, method="absolute"):
        '''
            Seek to a time position within the now playing media
            params:
                zone_or_output_id: the id of the zone or output
                seconds: The target seek position
                method: How to interpret the target seek position ('absolute'|'relative')
        '''
        data = {  "zone_or_output_id": zone_or_output_id, "how": method, "seconds": seconds }
        return self._request(ServiceTransport + "/seek", data)

    def shuffle(self, zone_or_output_id, shuffle=True):
        '''
            Enable/disable shuffle
            params:
                zone_or_output_id: the id of the output or zone
                shuffle: bool if shuffle should be enabled. False will disable shuffle
        '''
        data = {  "zone_or_output_id": zone_or_output_id, "shuffle": shuffle }
        return self._request(ServiceTransport + "/change_settings", data)

    def repeat(self, zone_or_output_id, repeat=True):
        '''
            Enable/disable repeat (loop mode)
            params:
                zone_or_output_id: the id of the output or zone
                repeat: bool if repeat should be enabled. False will disable shuffle
        '''
        loop = "loop" if repeat else "disabled"
        data = {  "zone_or_output_id": zone_or_output_id, "loop": loop }
        return self._request(ServiceTransport + "/change_settings", data)

    def register_state_callback(self, callback, event_filter=None, id_filter=None):
        '''
            register a callback to be informed about changes to zones or outputs
            params:
                callback: method to be called when state changes occur, it will be passed an event param as string and a list of changed objects
                          callback will be called with params:
                          - event: string with name of the event ("zones_changed", "zones_seek_changed", "outputs_changed")
                          - a list with the zone or output id's that changed
                event_filter: only callback if the event is in this list
                id_filter: one or more zone or output id's or names to filter on (list or string)
        '''
        if not event_filter:
            event_filter = []
        elif not isinstance(event_filter, list):
            event_filter = [event_filter]
        if not id_filter:
            id_filter = []
        elif not isinstance(id_filter, list):
            id_filter = [id_filter]
        self._state_callbacks.append( (callback, event_filter, id_filter) )

    def register_queue_callback(self, callback, zone_or_output_id=""):
        ''' 
            subscribe to queue change events
            callback: function which will be called with the updated data (provided as dict object
            zone_or_output_id: If provided, only listen for updates for this zone or output
        '''
        if zone_or_output_id:
            opt_data = {"zone_or_output_id": zone_or_output_id}
        else:
            opt_data = None
        self._roonsocket.subscribe(ServiceTransport, "queue", callback, opt_data)

    def browse_browse(self, opts):
        '''
            undocumented and complex browse call on the roon api
            reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        '''
        return self._request(ServiceBrowse + "/browse", opts)

    def browse_load(self, opts):
        '''
            undocumented and complex browse call on the roon api
            reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        '''
        return self._request(ServiceBrowse + "/load", opts)

    def browse_pop_all(self, opts):
        '''
            undocumented and complex browse call on the roon api
            reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        '''
        return self._request(ServiceBrowse + "/pop_all", opts)

    def browse_pop(self, opts):
        '''
            undocumented and complex browse call on the roon api
            reference: https://github.com/RoonLabs/node-roon-api-browse/blob/master/lib.js
        '''
        return self._request(ServiceBrowse + "/pop", opts)

    def browse_by_path(self, search_paths, zone_or_output_id="", offset=0, search_input=None):
        ''' 
            workaround to browse content by specifying the path to the content
            params: 
                search_paths: a list of names to look for in the hierarchie.
                              e.g. ["Playlists", "My Favourite Playlist"]
                zone_or_output_id: id of a zone or output on which behalf the search is performed.
                              can be ommitted for browsing but required for actions (play etc.)
                offset: a list will only return 100 items, to get more use the offset
            returns: a list of items (if found) as returned by the browse function
        '''
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
            for item in result["items"]:
                if item["title"] == search_for or search_input and item.get("input_prompt"):
                    opts["item_key"] = item["item_key"]
                    if item.get("input_prompt"):
                        opts["input"] = search_input
                    result = self.browse_browse(opts)
                    if result and  "list" in result and result["list"]["count"] > 100:
                        opts["offset"] = offset
                        opts["set_display_offset"] = offset
                    result = self.browse_load(opts)
        return result

    def playlists(self, offset=0):
        ''' return the list of playlists'''
        return self.browse_by_path(["Playlists"], offset=offset)

    def internet_radio(self, offset=0):
        ''' return the list of internet radio stations'''
        return self.browse_by_path(["Internet Radio"], offset=offset)

    def artists(self, offset=0):
        '''return the list of artists in the library'''
        return self.browse_by_path(["Library", "Artists"], offset=offset) 

    def albums(self, offset=0):
        '''return the list of albums in the library'''
        return self.browse_by_path(["Library", "Albums"], offset=offset)

    def tracks(self, offset=0):
        '''return the list of tracks in the library'''
        return self.browse_by_path(["Library", "Tracks"], offset=offset)

    def tags(self, offset=0):
        '''return the list of tags in the library'''
        return self.browse_by_path(["Library", "Tags"], offset=offset)

    def genres(self, subgenres_for="", offset=0):
        '''return the list of genres in the library'''
        return self.browse_by_path(["Genres", subgenres_for], offset=offset)

    def play_playlist(self, zone_or_output_id, playlist_title, shuffle=True):
        ''' play playlist by name on the specified zone'''
        play_action = "Shuffle" if shuffle else "Play Now"
        return self.browse_by_path(["Playlists", playlist_title, "Play Playlist", play_action], zone_or_output_id)

    def play_radio(self, zone_or_output_id, radio_title):
        ''' play internet radio by name on the specified zone'''
        return self.browse_by_path(["Internet Radio", radio_title, "Play Radio", "Play Now"], zone_or_output_id)

    def play_genre(self, zone_or_output_id, genre_name, subgenre="", shuffle=True):
        '''play specified genre on the specified zone'''
        action = "Shuffle" if shuffle else "Play Genre"
        if subgenre:
            return self.browse_by_path(["Genres", genre_name, subgenre, "Play Genre", action], zone_or_output_id)
        else:
            return self.browse_by_path(["Genres", genre_name, "Play Genre", action], zone_or_output_id)

    def search_artists(self, search_input):
        ''' search for artists by name'''
        return self.browse_by_path(["Library", "Search", "Artists"], search_input=search_input)



    ############# private methods ##################
    

    def __init__(self, appinfo, token=None, host=None, port=9100, blocking_init=True):
        '''
            Set up the connection with Roon
            appinfo: a dict of the required information about the app that should be connected to the api
            token: used for presistant storage of the auth token, will be set to token attribute if retrieved. You should handle saving of the key yourself
            host: optional the ip or hostname of the Roon server, will be auto discovered if ommitted
            port: optional the http port of the Roon websockets api. Should be default of 9100
            blocking_init: By default the init will halt untill the socket is connected and the app is authenticated, 
                           if you set bool to False te init will continue but you will only receive data once the connection is fully initialized. 
                           The latter is preferred if you're (only) using the callbacks
        '''
        if not isinstance(appinfo, dict):
            raise("appinfo is not in a valid format!") # TODO: add some more sanity checks
        if blocking_init:
            self._do_init()
        else:
            try:
                import thread as _thread #py2
            except ImportError:
                import _thread # py3
            _thread.start_new_thread(self._do_init, (appinfo, token, host, port))
        

    def _do_init(self, appinfo, token, host, port):
        ''' initialization of the api including registering'''
        LOGGER.info("Discovering Roon server in the network")
        while not host and not self._exit:
            host, port = RoonDiscovery().first()
            if not host and not self._exit:
                time.sleep(2)
            else:
                LOGGER.info("Discovered Roon server in the network at IP %s:%s" % (host, port))
        self._host = host
        self._port = port
        ws_address = "ws://%s:%s/api" %(host, port)
        self._roonsocket = RoonApiWebSocket(ws_address)
        self._roonsocket.start()
        # wait for the socket connection to open
        timeout = 0
        while not self._exit:
            if self._roonsocket.connected:
                break
            elif timeout == 100:
                LOGGER.error("Failed to connect to socket! Will keep retrying...")
                timeout = 0
            elif self._exit:
                return
            time.sleep(0.5)
            timeout += 1
        # authenticate
        self._token = token
        self._register_app(appinfo)
        # once we're passed the registration we can set the init flag
        self.init_complete = True
        # fill zones and outputs dicts one time so the data is available right away
        self._zones = self._get_zones()
        self._outputs = self._get_outputs()
        # subscribe to state change events
        self._roonsocket.subscribe(ServiceTransport, "zones", self._on_state_change)
        self._roonsocket.subscribe(ServiceTransport, "outputs", self._on_state_change)
        

    def __exit__(self, type, value, tb):
        self.stop()

    def __enter__(self):
        return self

    def stop(self):
        self._exit = True
        if self._roonsocket:
            self._roonsocket.stop()

    def _on_state_change(self, msg):
        ''' process messages we receive from the roon websocket into a more usable format'''
        events = []
        for state_key, state_values in msg.items():
            changed_ids = []
            filter_keys = []
            if state_key in ["zones_seek_changed", "zones_changed", "zones_added", "zones"]:
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
                event = "zones_seek_changed" if state_key == "zones_seek_changed" else "zones_changed"
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
                except Exception:
                    LOGGER.exception("Error while executing callback!")

    def _get_outputs(self):
        outputs = {}
        data = self._request(ServiceTransport + "/get_outputs")
        if data:
            for output in data["outputs"]:
                outputs[output["output_id"]] = output
        return outputs

    def _get_zones(self):
        zones = {}
        data = self._request(ServiceTransport + "/get_zones")
        if data:
            for zone in data["zones"]:
                zones[zone["zone_id"]] = zone
        return zones

    def _register_app(self, appinfo):
        ''' register this app with roon and wait for the authentication token'''
        # warning: at first launch this will block untill the user approves the app within Roon.
        if not appinfo or not isinstance(appinfo, dict):
            raise("appinfo missing or in incorrect format!")
        if not appinfo.get("required_services"):
            appinfo["required_services"] = [ServicePing, ServiceTransport, ServiceBrowse]
        if not appinfo.get("optional_services"):
            appinfo["optional_services"] = []
        if not appinfo.get("provided_services"):
            appinfo["provided_services"] = []
        if self._token:
            appinfo["token"] = self._token
        request_id = self._roonsocket.send(ServiceRegistry + "/register", appinfo)
        if not self._token:
            LOGGER.info("The application should be approved within Roon's settings.")
        else:
            LOGGER.info("Registering the app with Roon...")
        while not self._exit:
            if self._roonsocket.results.get(request_id):
                _token = self._roonsocket.results[request_id].get("token")
                if _token:
                    LOGGER.info("Registered to Roon server %s" % self._roonsocket.results[request_id]["display_name"])
                    LOGGER.debug(self._roonsocket.results[request_id])
                    self._token = _token
                    del self._roonsocket.results[request_id]
                    break
            time.sleep(1)

    def _request(self, command, data=None):
        ''' send command and wait for result '''
        if not self.init_complete:
            LOGGER.warning("socket is not yet ready")
            return None
        request_id = self._roonsocket.send(command, data)
        result = None
        retries = 20
        while retries:
            result = self._roonsocket.results.get(request_id)
            if result:
                break
            else:
                retries -= 1
                time.sleep(0.1)
        del self._roonsocket.results[request_id]
        return result



    