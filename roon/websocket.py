import websocket
import threading
from .constants import *

try:
    import simplejson as json
except ImportError:
    import json


class RoonApiWebSocket(threading.Thread):
    _socket = None
    _results = {}
    _subscriptions = {}
    _requestid = 0
    _subkey = 0
    _exit = False
    connected = False

    @property
    def results(self):
        return self._results

    def run(self):
        while not self._exit:
            try:
               self._socket.run_forever() # within try-except to handle connection loss
            except:
                pass # TODO: should we also add the subscriptions again ?

    def stop(self):
        self._exit = True
        for key, value in self._subscriptions.items():
            self.unsubscribe(value["service"], value["endpoint"])
        self._socket.close()

    def __init__(self, host):
        self._socket = websocket.WebSocketApp(host, 
                on_message=self.on_message, 
                on_error=self.on_error, 
                on_open=self.on_open, 
                on_close=self.on_close)
        threading.Thread.__init__(self)
        self.daemon = True
        
    def subscribe(self, service, endpoint, callback, opt_data=None):
        '''subscribe to events'''
        subkey = self._subkey
        self._subkey += 1
        data = {"subscription_key": subkey}
        if opt_data and isinstance(opt_data, dict):
            data.update(opt_data)
        request_id = self.send(service + "/subscribe_" + endpoint, data)
        self._subscriptions[request_id] = {
            "service": service,
            "endpoint": endpoint,
            "request_id": request_id,
            "subkey": subkey,
            "callback": callback
        }

    def unsubscribe(self, service, endpoint):
        '''subscribe to events'''
        matches = []
        for key, value in self._subscriptions.items():
            if value["service"] == service and value["endpoint"] == endpoint:
                matches.append((key, value["subkey"]))
        for item in matches:
            self.send(service + "/unsubscribe_" + endpoint, {"subscription_key": item[1]})
            del self._subscriptions[item[0]]


    def on_message(self, ws, message):
        try:
            lines = message.split("\n")
            header = lines[0].decode("utf-8")
            content_type = lines[1].split("Content-Type: ")[1].decode("utf-8")
            request_id = int(lines[2].split("Request-Id: ")[1])
            content_length = int(lines[3].split("Content-Length: ")[1])
            body = "".join(lines[5:]).decode("utf-8")
            if body and "{" in body:
                body = json.loads(body)
            if request_id in self._subscriptions:
                self._subscriptions[request_id]["callback"](body)
            else:
                self._results[request_id] = body
        except Exception as exc:
            LOGGER.warning("Received malformed message (%s)\n%s" %(str(exc, message)))

    def on_error(self, ws, error):
        LOGGER.error(error)

    def on_close(self, ws):
        LOGGER.info("session closed")
        self.connected = False

    def on_open(self, ws):
        LOGGER.debug('Opened Websocket connection to the server...')
        self.connected = True

    def send(self, command, body=None, content_type="application/json"):
        request_id = self._requestid
        self._requestid += 1
        self._results[request_id] = None
        if body == None:
            msg = "MOO/1 REQUEST %s\nRequest-Id: %s\n\n" % (command, request_id)
        else:
            body = json.dumps(body)
            msg = "MOO/1 REQUEST %s\nRequest-Id: %s\nContent-Length: %s\nContent-Type: %s\n\n%s" %(command, request_id, len(body), content_type, body)
        self._socket.send(msg, 0x2)
        return request_id
