import time
from .constants import *
from .roonapisocket import RoonApiWebSocket
from .discovery  import RoonDiscovery


class RoonApi():
    _roonsocket = None
    _exit = False
    _zones = {}
    _outputs = {}
    _state_callbacks = []

    @property
    def zones(self):
        return self._zones if self._zones else self._get_zones()

    @property
    def outputs(self):
        return self._outputs if self._outputs else self._get_outputs()

    def zone_by_name(self, zone_name):
        for zone in self.zones.values():
            if zone["display_name"] == zone_name:
                return zone
        return None

    def output_by_name(self, output_name):
        for output in self.outputs.values():
            if output["display_name"] == output_name:
                return output
        return None

    def zone_by_output_id(self, output_id):
        for zone in self.zones.values():
            for output in zone["outputs"]:
                if output["output_id"] == output_id:
                    return zone
        return None

    def zone_by_output_name(self, output_name):
        for zone in self.zones.values():
            for output in zone["outputs"]:
                if output["display_name"] == output_name:
                    return zone
        return None

    def playback_control(self, zone_or_output_id, control="play"):
        '''
            send player command to the specified zone
            param control:
                 * "play" - If paused or stopped, start playback
                 * "pause" - If playing or loading, pause playback
                 * "playpause" - If paused or stopped, start playback. If playing or loading, pause playback.
                 * "stop" - Stop playback and release the audio device immediately
                 * "previous" - Go to the start of the current track, or to the previous track
                 * "next" - Advance to the next track
             param output_id: the id of the zone or output
        '''
        data = {
                   "zone_or_output_id": zone_or_output_id,
                   "control":           control
                }
        return self._request(ServiceTransport + "/control", data)

    def register_state_callback(self, callback, event_filter=None, id_filter=None):
        '''
            register a callback to be informed about changes to zones or outputs
            callback: method to be called when state changes occur, it will be passed an event param as string and a list of changed objects
                      callback will be called with params:
                      - event: string with name of the event ("zones_changed", "zones_seek_changed", "outputs_changed")
                      - a list with the id's that changed
            event_filter: only callback if the event is in this list
            id_filter: one or more zone or output id's or names to filter on (list or string)
        '''
        if not event_filter:
            event_filter = []
        elif isinstance(event_filter, (str, unicode)):
            event_filter = [event_filter]
        if not id_filter:
            id_filter = []
        elif isinstance(id_filter, (str, unicode)):
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


    ############# private methods ##################
    

    def __init__(self, appinfo, token=None, host=None, port=9100):
        '''
            Set up the connection with Roon
            appinfo: a dict of the required information about the app that should be connected to the api
            token: used for presistant storage of the auth token, will be get and set so handle saving of the key yourself
            host: optional the ip or hostname of the Roon server, will be auto discovered if ommitted
            port: optional the http port of the Roon websockets api. Should be default of 9100
        '''
        while not host and not self._exit:
            LOGGER.info("Discovering Roon server in the network")
            host, port = RoonDiscovery().first()
            if not host:
                time.sleep(10)
            else:
                LOGGER.info("Discovered Roon server in the network at IP %s" % host)
        ws_address = "ws://%s:%s/api" %(host, port)
        self._roonsocket = RoonApiWebSocket(ws_address)
        self._roonsocket.start()
        # wait for the socket connection to open
        timeout = 0
        while not self._exit:
            if self._roonsocket.connected:
                break
            elif timeout == 100:
                LOGGER.error("Failed to connect to socket!")
                return
            elif self._exit:
                return
            time.sleep(0.5)
            timeout += 1
        # authenticate
        self._register_app(appinfo, token)
        # subscribe to state change events
        self._roonsocket.subscribe(ServiceTransport, "zones", self._on_state_change)
        self._roonsocket.subscribe(ServiceTransport, "outputs", self._on_state_change)

    def __exit__(self):
        self.stop()

    def stop(self):
        self._exit = True
        if self._roonsocket:
            self._roonsocket.stop()

    def _on_state_change(self, msg):
        changed_ids = []
        filter_keys = []
        event = ""
        for state_key, state_values in msg.items():
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
                    if state_key == "zones_seek_changed":
                        event = "zones_seek_changed"
                    else:
                        event = "zones_changed"
            elif state_key in ["outputs_changed", "outputs_added", "outputs"]:
                for output in state_values:
                    if output["output_id"] in self._outputs:
                        self._outputs[output["output_id"]].update(zone)
                    else:
                        self._outputs[output["output_id"]] = output
                    changed_ids.append(zone["zone_id"])
                    filter_keys.append(zone["display_name"])
                    event = "outputs_changed"
            elif state_key == "zones_removed":
                for item in state_values:
                    del self._zones[item]
            elif state_key == "outputs_removed":
                for item in state_values:
                    del self._outputs[item]
            else:
                LOGGER.warning("unknown state change: %s" % msg)
        if not event or not changed_ids:
            return
        filter_keys.extend(changed_ids)
        for item in self._state_callbacks:
            callback = item[0]
            event_filter = item[1]
            id_filter = item[2]
            if event_filter and (event not in event_filter):
                continue
            if id_filter and set(id_filter).isdisjoint(filter_keys):
                continue
            callback(event, changed_ids)

    def _get_outputs(self):
        return self._request(ServiceTransport + "/get_outputs")

    def _get_zones(self):
        return self._request(ServiceTransport + "/get_zones")

    def _register_app(self, appinfo, token):
        ''' register this app with roon and wait for the authentication token'''
        if not appinfo or not isinstance(appinfo, dict):
            raise("appinfo missing or in incorrect format!")
        if not appinfo.get("required_services"):
            appinfo["required_services"] = [ServicePing, ServiceTransport]
        if not appinfo.get("optional_services"):
            appinfo["optional_services"] = []
        if not appinfo.get("provided_services"):
            appinfo["provided_services"] = []
        appinfo["token"] = token
        request_id = self._roonsocket.send(ServiceRegistry + "/register", appinfo)
        LOGGER.debug("waiting for authentication...")
        while not self._exit:
            if self._roonsocket.results.get(request_id):
                token = self._roonsocket.results[request_id].get("token")
                if token:
                    LOGGER.info("Registered to Roon server %s" % self._roonsocket.results[request_id]["display_name"])
                    LOGGER.debug(self._roonsocket.results[request_id])
                    del self._roonsocket.results[request_id]
                    break
            time.sleep(1)

    def _request(self, command, data=None):
        ''' send command and wait for result '''
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



    