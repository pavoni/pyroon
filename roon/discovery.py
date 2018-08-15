import threading
import socket
import os.path
from .constants import *

class RoonDiscovery(object):
    """Class to discover Roon Servers connected in the network."""

    def __init__(self):
        self.entries = []
        self.last_scan = None
        self._lock = threading.RLock()

    def scan(self, single=False):
        """Scan the network for servers."""
        with self._lock:
            self.update(single)

    def all(self, single=False):
        """Scan and return all found entries as a list. Each server is a tuple of host,port."""
        self.scan(single)
        return list(self.entries)

    def first(self):
        ''' returns first server that is found'''
        all_servers = self.all(True)
        return all_servers[0] if all_servers else (None, None)

    def update(self, single=False):
        """update the server entry with details"""
        this_dir = os.path.dirname(os.path.abspath(__file__))
        sood_file = os.path.join(this_dir, ".soodmsg")
        with open(sood_file) as f:
            msg = f.read()
        entries = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5)
        sock.bind(('', 0))
        try:
            sock.sendto(msg, ('<broadcast>', 9003))
            while True:
                try:
                    data, server = sock.recvfrom(1024)
                    lines = []
                    for line in data.split("\n"):
                        lines.extend(line.split("\x04"))
                    if "SOOD" in lines[0] and len(lines) > 6 and "http_port" in lines[4]:
                        # match for Roon server found!
                        port = int(lines[5].encode("utf-8").strip())
                        host = server[0]
                        entries.append((host, port))
                        if single:
                            # we're only interested in the first server found
                            break
                except socket.timeout:
                    break
                except Exception as exc:
                    LOGGER.exception(exc)
        finally:
            sock.close()
        self.entries = entries
    