from __future__ import unicode_literals
import threading
import socket
import os.path
from .constants import *

class RoonDiscovery(threading.Thread):
    """Class to discover Roon Servers connected in the network."""
    _exit = threading.Event()
    _discovered_callback = None

    def __init__(self, callback):
        self._discovered_callback = callback
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        ''' run discovery untill server found '''
        while not self._exit.isSet():
            host, port = self.first()
            if host:
                self._discovered_callback(host, port)
                self.stop()

    def stop(self):
        self._exit.set()

    def all(self):
        """Scan and return all found entries as a list. Each server is a tuple of host,port."""
        self.discover(first_only=False)

    def first(self):
        ''' returns first server that is found'''
        all_servers = self._discover(first_only=True)
        return all_servers[0] if all_servers else (None, None)

    def _discover(self, first_only=False):
        """update the server entry with details"""
        this_dir = os.path.dirname(os.path.abspath(__file__))
        sood_file = os.path.join(this_dir, ".soodmsg")
        with open(sood_file) as f:
            msg = f.read()
        msg = msg.encode()
        entries = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5)
        sock.bind(('', 0))
        try:
            sock.sendto(msg, ('<broadcast>', 9003))
            while not self._exit.isSet():
                try:
                    data, server = sock.recvfrom(1024)
                    data = data.decode()
                    lines = []
                    for line in data.split("\n"):
                        lines.extend(line.split("\x04"))
                    if "SOOD" in lines[0] and len(lines) > 6 and "http_port" in lines[4]:
                        # match for Roon server found!
                        port = int(lines[5].encode("utf-8").strip())
                        host = server[0]
                        entries.append((host, port))
                        if first_only:
                            # we're only interested in the first server found
                            break
                except socket.timeout:
                    break
                except Exception as exc:
                    LOGGER.exception(exc)
        finally:
            sock.close()
        return entries
    