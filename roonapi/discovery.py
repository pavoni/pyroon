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


def local_ip():
    """Get the local ip addresses (so they can be excluded."""
    addresses = socket.getaddrinfo(
        socket.gethostname(), None, family=socket.AF_INET, proto=socket.IPPROTO_UDP
    )
    return {ad[4][0] for ad in addresses}


class RoonDiscovery(threading.Thread):
    """Class to discover Roon Servers connected in the network."""

    _exit = threading.Event()
    _discovered_callback = None

    def __init__(self, callback):
        """Discover Roon Servers connected in the network."""
        self._discovered_callback = callback
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        """Run discovery until server found."""
        while not self._exit.isSet():
            host, port = self.first()
            if host:
                self._discovered_callback(host, port)
                self.stop()

    def stop(self):
        """Stop scan."""
        self._exit.set()

    def all(self):
        """Scan and return all found entries as a list. Each server is a tuple of host,port."""
        self._discover(first_only=False)

    def first(self):
        """Return first server that is found."""
        all_servers = self._discover(first_only=True)
        return all_servers[0] if all_servers else (None, None)

    # pylint: disable=too-many-locals
    def _discover(self, first_only=False, exclude_self=True):
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
            sock.settimeout(5)
            sock.sendto(msg, (SOOD_MULTICAST_IP, SOOD_PORT))
            own_ip = local_ip()
            while not self._exit.isSet():
                try:
                    data, server = sock.recvfrom(1024)
                    message = SOODMessage(data).as_dictionary

                    host = server[0]
                    port = message["properties"]["http_port"]
                    if exclude_self and host in own_ip:
                        LOGGER.debug(
                            "Ignoring server with address %s, because it's on this machine",
                            host,
                        )
                        continue
                    entries.append((host, port))
                    if first_only:
                        # we're only interested in the first server found
                        break
                except socket.timeout:
                    LOGGER.info("Timeout")
                    break
                except FormatException as format_exception:
                    LOGGER.error("Format exception %s", format_exception.message)
                    break
        return entries
