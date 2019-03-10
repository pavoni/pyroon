"""
Module defining a class to discover Roon servers.

If multiple servers are available on the network, the first to be discovered
is selected. This may not be the one you have enabled the plugin for.
"""

import threading
import socket
import os.path
from .soodmessage import SOODMessage, FormatException


class RoonDiscovery(threading.Thread):
    """Class to discover Roon Servers connected in the network."""
    _exit = threading.Event()
    _discovered_callback = None

    def __init__(self, callback):
        self._discovered_callback = callback
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        ''' run discovery until server found '''
        while not self._exit.isSet():
            host, port = self.first()
            if host:
                self._discovered_callback(host, port)
                self.stop()

    def stop(self):
        self._exit.set()

    def all(self):
        """Scan and return all found entries as a list. Each server is a tuple of host,port."""
        self._discover(first_only=False)

    def first(self):
        ''' returns first server that is found'''
        all_servers = self._discover(first_only=True)
        return all_servers[0] if all_servers else (None, None)

    def _discover(self, first_only=False):
        """update the server entry with details"""
        this_dir = os.path.dirname(os.path.abspath(__file__))
        sood_file = os.path.join(this_dir, ".soodmsg")
        with open(sood_file) as sood_query_file:
            msg = sood_query_file.read()
        msg = msg.encode()
        entries = []
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(5)
            sock.bind(('', 0))
            sock.sendto(msg, ('<broadcast>', 9003))
            while not self._exit.isSet():
                try:
                    data, server = sock.recvfrom(1024)
                    message = SOODMessage(data).as_dictionary
                    host = server[0]
                    port = message["properties"]["http_port"]
                    entries.append((host, port))
                    if first_only:
                        # we're only interested in the first server found
                        break
                except socket.timeout:
                    print("timeout")
                    break
                except FormatException as format_exception:
                    print(format_exception.message)
                    break
        return entries
