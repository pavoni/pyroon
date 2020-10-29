from __future__ import unicode_literals
import websocket
import threading
from .constants import LOGGER, ControlSource, ControlVolume, ServicePing

try:
    import simplejson as json
except ImportError:
    import json

try:
    import thread
except ImportError:
    import _thread as thread


class RoonApiWebSocket(threading.Thread):
    """Class to handle the roon websocket connection."""

    _socket = None
    _results = {}
    _requestid = 10  # initial request_id of 10 to prevent confusion with the requests that are sent by the server at initialization
    _subkey = 0
    _exit = False
    _subscriptions = {}
    source_controls_callback = None
    volume_controls_callback = None
    connected_callback = None
    registered_calback = None
    connected = False
    failed_state = False

    @property
    def results(self):
        """Return the result of the previous request."""
        return self._results

    def run(self):
        """Start the socket thread."""
        self._socket.run_forever(ping_interval=10)
        if not self._exit:
            LOGGER.warning("Session unexpectedly disconnected!")
            self._exit = True
            self.failed_state = True
        else:
            LOGGER.debug("socket connection closed")

    def stop(self):
        """Stop the socket thread."""
        self._exit = True
        subscriptions = []
        for key, value in self._subscriptions.items():
            subscriptions.append((value["service"], value["endpoint"]))
        for service, endpoint in subscriptions:
            self.unsubscribe(service, subscriptions)
        self._socket.close()

    def __init__(self, host):
        """Create the websocket connection to the roon server."""
        self._socket = websocket.WebSocketApp(
            host,
            on_message=self.on_message,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close,
        )
        threading.Thread.__init__(self)
        self.daemon = True

    def subscribe(self, service, endpoint, callback, opt_data=None):
        """Subscribe to events."""
        subkey = self._subkey
        self._subkey += 1
        data = {"subscription_key": subkey}
        if opt_data and isinstance(opt_data, dict):
            data.update(opt_data)
        request_id = self.send_request(service + "/subscribe_" + endpoint, data)
        self._subscriptions[request_id] = {
            "service": service,
            "endpoint": endpoint,
            "request_id": request_id,
            "subkey": subkey,
            "callback": callback,
        }

    def unsubscribe(self, service, endpoint):
        """Subscribe to events."""
        matches = []
        for key, value in self._subscriptions.items():
            if value["service"] == service and value["endpoint"] == endpoint:
                matches.append((key, value["subkey"]))
        for item in matches:
            self.send_request(
                service + "/unsubscribe_" + endpoint, {"subscription_key": item[1]}
            )
            del self._subscriptions[item[0]]

    def on_message(self, ws, message=None):
        """Handle message callback."""
        if not message:
            message = (
                ws  # compatability fix because of change in websocket-client v0.49
            )
        try:
            message = message.decode("utf-8")
            lines = message.split("\n")
            header = lines[0]
            body = ""
            if "Content-Type:" in message:
                request_id = int(lines[2].split("Request-Id: ")[1])
                body = "".join(lines[5:])
            elif "Logging:" in message:
                request_id = int(lines[2].split("Request-Id: ")[1])
            else:
                request_id = int(lines[1].split("Request-Id: ")[1])
                body = header
            if body and "{" in body:
                body = json.loads(body)
            # handle message
            if ControlSource in header:
                # incoming message for source_control endpoint
                event = header.split("/")[-1]
                if self.source_controls_callback:
                    self.source_controls_callback(event, request_id, body)
            elif ControlVolume in header:
                # incoming message for volume_control endpoint
                event = header.split("/")[-1]
                if self.volume_controls_callback:
                    self.volume_controls_callback(event, request_id, body)
            elif ServicePing in header:
                # reply to incoming ping from server
                self.send_complete(request_id, "Success")
            elif "Registered" in header:
                if self.registered_calback:
                    self.registered_calback(body)
            elif request_id in self._subscriptions:
                # this is callback for one of our subscriptions
                self._subscriptions[request_id]["callback"](body)
            else:
                # this is just a result for one of our requests
                self._results[request_id] = body
        except Exception:
            LOGGER.exception("Error while parsing message")
            LOGGER.debug(message)

    def on_error(self, ws, error=None):
        """Handle error callback."""
        if not error:
            error = ws  # compatability fix because of change in websocket-client v0.49
        LOGGER.error(error)

    def on_close(self, ws=None):
        """Handle closing the session."""
        LOGGER.info("session closed")
        self.connected = False
        self._requestid = 10
        self._subkey = 0
        self._subscriptions = {}

    def on_open(self, ws=None):
        """Handle opening the session."""
        LOGGER.debug("Opened Websocket connection to the server...")
        self.connected = True
        if self.connected_callback:
            thread.start_new_thread(self.connected_callback, ())

    def send_continue(self, request_id, body):
        """Send continue message if socket open."""
        if not self.connected:
            LOGGER.error("Connection is not (yet) ready!")
            return False
        body = json.dumps(body)
        msg = (
            "MOO/1 CONTINUE Changed\nRequest-Id: %s\nContent-Length: %s\nContent-Type: application/json\n\n%s"
            % (request_id, len(body), body)
        )
        msg = bytes(msg, "utf-8")
        self._socket.send(msg, 0x2)

    def send_complete(self, request_id, name, body=""):
        """Send complete message if socket open."""
        if not self.connected:
            LOGGER.error("Connection is not (yet) ready!")
            return False
        msg = "MOO/1 COMPLETE %s\nRequest-Id: %s" % (name, request_id)
        if body:
            body = json.dumps(body)
            msg += "\nContent-Length: %s\nContent-Type: application/json\n\n%s" % (
                len(body),
                body,
            )
        else:
            msg += "\n\n"
        msg = bytes(msg, "utf-8")
        self._socket.send(msg, 0x2)

    def send_request(
        self, command, body=None, content_type="application/json", header_type="REQUEST"
    ):
        """Send request to the roon sever."""
        if not self.connected:
            LOGGER.error("Connection is not (yet) ready!")
            return False
        request_id = self._requestid
        self._requestid += 1
        self._results[request_id] = None
        if body is None:
            msg = "MOO/1 REQUEST %s\nRequest-Id: %s\n\n" % (command, request_id)
        else:
            body = json.dumps(body)
            msg = (
                "MOO/1 REQUEST %s\nRequest-Id: %s\nContent-Length: %s\nContent-Type: %s\n\n%s"
                % (command, request_id, len(body), content_type, body)
            )
        msg = bytes(msg, "utf-8")
        self._socket.send(msg, 0x2)
        return request_id
