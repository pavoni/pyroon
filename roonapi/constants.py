from __future__ import unicode_literals

import logging

SOOD_PORT = 9003
SOOD_MULTICAST_IP = "239.255.90.90"

SERVICE_REGISTRY = "com.roonlabs.registry:1"
SERVICE_TRANSPORT = "com.roonlabs.transport:2"
SERVICE_STATUS = "com.roonlabs.status:1"
SERVICE_PAIRING = "com.roonlabs.pairing:1"
SERVICE_PING = "com.roonlabs.ping:1"
SERVICE_IMAGE = "com.roonlabs.image:1"
SERVICE_BROWSE = "com.roonlabs.browse:1"
SERVICE_SETTINGS = "com.roonlabs.settings:1"
CONTROL_VOLUME = "com.roonlabs.volumecontrol:1"
CONTROL_SOURCE = "com.roonlabs.sourcecontrol:1"

REGISTERED = "Registered"

MESSAGE_REQUEST = "REQUEST"
MESSAGE_COMPLETE = "COMPLETE"
MESSAGE_CONTINUE = "CONTINUE"

PAGE_SIZE = 100

LOG_FORMAT = logging.Formatter(
    "%(asctime)-15s %(levelname)-5s  %(module)s -- %(message)s"
)
LOGGER = logging.getLogger("roonapi")
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setFormatter(LOG_FORMAT)
LOGGER.addHandler(CONSOLE_HANDLER)
LOGGER.setLevel(logging.INFO)
