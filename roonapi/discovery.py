"""
Module defining a class to discover Roon servers.

If multiple servers are available on the network, the first to be discovered
is selected. This may not be the one you have enabled the plugin for.
"""

import os.path
import socket
import threading

from .soodmessage import FormatException, SOODMessage
from .constants import SOOD_PORT, SOOD_MULTICAST_IP, LOGGER


class RoonDiscovery(threading.Thread):
    """Class to discover Roon Servers connected in the network."""

    def __init__(self, core_id=None):
        """Discover Roon Servers connected in the network."""
        self._exit = threading.Event()
        self._core_id = core_id
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        """Run discovery until server found."""
        while not self._exit.isSet():
            host, _ = self.first()
            if host:
                self.stop()

    def stop(self):
        """Stop scan."""
        self._exit.set()

    def all(self):
        """Scan and return all found entries as a list. Each server is a tuple of host,port."""
        return self._discover(first_only=False)

    def first(self):
        """Return first server that is found."""
        all_servers = self._discover(first_only=True)
        return all_servers[0] if all_servers else (None, None)

    # pylint: disable=too-many-locals,unspecified-encoding
    def _discover(self, first_only=False):
        """Update the server entry with details."""
        this_dir = os.path.dirname(os.path.abspath(__file__))
        sood_file = os.path.join(this_dir, ".soodmsg")
        with open(sood_file) as sood_query_file:
            msg = sood_query_file.read()
        msg = msg.encode()
        entries = []

        with socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        ) as sock:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
            sock.sendto(msg, (SOOD_MULTICAST_IP, SOOD_PORT))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(msg, ("<broadcast>", SOOD_PORT))
            sock.settimeout(5)
            while not self._exit.isSet():
                try:
                    data, server = sock.recvfrom(1024)
                    message = SOODMessage(data).as_dictionary

                    host = server[0]
                    port = message["properties"]["http_port"]
                    unique_id = message["properties"]["unique_id"]
                    LOGGER.debug("Discovered %s", message)

                    if self._core_id is not None and self._core_id != unique_id:
                        LOGGER.debug(
                            "Ignoring server with id %s, because we're looking for %s",
                            unique_id,
                            self._core_id,
                        )
                        continue

                    entries.append((host, port))
                    if first_only:
                        # we're only interested in the first server found
                        break
                except socket.timeout:
                    LOGGER.debug("Timeout")
                    break
                except FormatException as format_exception:
                    LOGGER.error("Format exception %s", format_exception.message)
                    break
        return entries
