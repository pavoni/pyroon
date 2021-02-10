from __future__ import unicode_literals

import threading

import websocket

from .constants import LOGGER, REGISTERED, SERVICE_PING

try:
    import simplejson as json
except ImportError:
    import json

try:
    import thread
except ImportError:
    import _thread as thread


class RoonApiWebSocket(
    threading.Thread
):  # pylint: disable=too-many-instance-attributes
    """Class to handle the roon websocket connection."""

    @property
    def results(self):
        """Return the result of the previous request."""
        return self._results

    def register_connected_callback(self, callback):
        """To be called on connection."""
        self._connected_callback = callback

    def register_registered_calback(self, callback):
        """To be called on registration."""
        self._registered_calback = callback

    def register_source_controls_callback(self, callback):
        """To be called on source changes."""
        self._volume_controls_callback = callback

    def register_volume_controls_callback(self, callback):
        """To be called on volume changes."""
        self._volume_controls_callback = callback

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
        for _, value in self._subscriptions.items():
            subscriptions.append((value["service"], value["endpoint"]))
        for service, _ in subscriptions:
            self.unsubscribe(service, subscriptions)
        self._socket.close()

    def __init__(self, host):
        """Create the websocket connection to the roon server."""

        self._socket = None
        self._results = {}
        self._requestid = 10  # initial request_id of 10 to prevent confusion with the requests that are sent by the server at initialization
        self._subkey = 0
        self._exit = False
        self._subscriptions = {}
        self.connected = False
        self.failed_state = False

        self._connected_callback = lambda: None
        self._registered_calback = lambda _: None
        self._source_controls_callback = lambda _a, _b, _c: None
        self._volume_controls_callback = lambda _a, _b, _c: None

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

    # pylint: disable=too-many-branches
    def on_message(self, w_socket, message=None):
        """Handle message callback."""
        if not message:
            message = w_socket  # compatability fix because of change in websocket-client v0.49
        try:
            message = message.decode("utf-8")
            lines = message.split("\n")
            header = lines[0]
            body = ""

            request_id = None
            line_with_request_id = [
                line for line in lines if line.startswith("Request-Id")
            ]
            if line_with_request_id:
                request_id = int(line_with_request_id[0].split("Request-Id: ")[1])

            if "Content-Type:" in message:
                # Roon uses a blank line after the header to indicate body.
                # See https://github.com/RoonLabs/node-roon-api/blob/master/moomsg.js#L45
                body = "".join(message.split("\n\n")[1:])
            elif "Logging:" not in message:
                body = header
            if body and "{" in body:
                body = json.loads(body)
            # handle message
            if SERVICE_PING in header:
                # reply to incoming ping from server
                self.send_complete(request_id, "Success")
            elif REGISTERED in header:
                self._registered_calback(body)
            elif request_id in self._subscriptions:
                # this is callback for one of our subscriptions
                self._subscriptions[request_id]["callback"](body)
            else:
                # this is just a result for one of our requests
                self._results[request_id] = body
        except websocket.WebSocketConnectionClosedException:
            # This can happen while closing a connection - so ignore
            pass

        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Error while parsing message '%s'", message)

    # pylint: disable=no-self-use
    def on_error(self, w_socket, error=None):
        """Handle error callback."""
        if not error:
            error = w_socket  # compatability fix because of change in websocket-client v0.49
        LOGGER.info("on_error %s", error)

    # pylint: disable=unused-argument
    def on_close(self, w_socket=None):
        """Handle closing the session."""
        LOGGER.debug("session closed")
        self.connected = False
        self._requestid = 10
        self._subkey = 0
        self._subscriptions = {}

    # pylint: disable=unused-argument
    def on_open(self, w_socket=None):
        """Handle opening the session."""
        LOGGER.debug("Opened Websocket connection to the server...")
        self.connected = True
        thread.start_new_thread(self._connected_callback, ())

    def send_continue(self, request_id, body):
        """Send continue message if socket open."""
        if not self.connected:
            LOGGER.error("Connection is not (yet) ready!")
            return
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
            return
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
