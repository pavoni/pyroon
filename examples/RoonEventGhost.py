import sys
# path to roonapi folder
sys.path.append('\\pyRoon\\pyRoonLibrary\\pyroon-master\\roonapi')
import roonapi, discovery, constants
import time, os
import json
import socket
import subprocess, shlex
from constants import LOGGER

settings = None
dataFolder = None
dataFile = None
inDebugger = getattr(sys, 'gettrace', None)
appinfo = {
    "extension_id": "sonnabend.roon.egvolume",
    "display_name": "EG Volume",
    "display_version": "1.0.0",
    "publisher": "sonnabend",
    "email": "",
}
roon = None


def main():
    try:
        global roon
        global settings
        loadSettings()
        # authorize if necessary
        try:
            if settings["core_id"].strip() == "" or settings["token"] == "":
                authorize()
        except:
            authorize()
        # connect to Roon core
        roon = connect(settings["core_id"], settings["token"])
        settings["core_id"] = roon.core_id
        settings["token"] = roon.token
        # subscribe to status notifications
        # roon.register_state_callback(state_change_callback)
        hostname = socket.gethostname()
        roon.register_volume_control("1", hostname, volume_control_callback, 0, "incremental")
        while True:
            time.sleep(0.1)
            pass

    finally:
        #finally, save settings
        if not (settings is None):
            saveSettings()

def connect(core_id, token):
    LOGGER.info("in connect\n  core_id: %s\n  token: %s" % (core_id,token))
    global appinfo
    try:
        discover = discovery.RoonDiscovery(core_id, dataFolder)
        LOGGER.info("discover object: %s" % discover)
        server = discover.first()
        LOGGER.info("server object: %s:%s" % (server[0], server[1]))
        roon = roonapi.RoonApi(appinfo, token, server[0], server[1], True)
        LOGGER.info("roon object: %s" % roon)
        return roon
    except:
        return None
    finally:
        discover.stop()

def authorize():
    LOGGER.info("authorizing")
    global appinfo
    global settings

    LOGGER.info("discovering servers")
    discover = discovery.RoonDiscovery(None)
    servers = discover.all()
    LOGGER.info("discover: %s\nservers: %s" % (discover, servers))

    LOGGER.info("Shutdown discovery")
    discover.stop()

    LOGGER.info("Found the following servers")
    LOGGER.info(servers)
    apis = [roonapi.RoonApi(appinfo, None, server[0], server[1], False) for server in servers]

    auth_api = []
    while len(auth_api) == 0:
        LOGGER.info("Waiting for authorisation")
        time.sleep(1)
        auth_api = [api for api in apis if api.token is not None]

    api = auth_api[0]

    LOGGER.info("Got authorisation")
    LOGGER.info("   host ip: " + api.host)
    LOGGER.info("   core name: " + api.core_name)
    LOGGER.info("   core id: " + api.core_id)
    LOGGER.info("   token: " + api.token)
    # This is what we need to reconnect
    settings["core_id"] = api.core_id
    settings["token"] = api.token

    LOGGER.info("leaving authorize with settings: %s" % settings)

    LOGGER.info("Shutdown apis")
    for api in apis:
        api.stop()


def state_change_callback(event, changed_ids):
    global roon
    """Call when something changes in roon."""
    LOGGER.info("\n-----")
    LOGGER.info("state_change_callback event:%s changed_ids: %s" % (event, changed_ids))
    LOGGER.info(" ")
    for zone_id in changed_ids:
        zone = roon.zones[zone_id]
        LOGGER.info("zone_id:%s zone_info: %s" % (zone_id, zone))

def volume_control_callback(control_key, event, value):
    global roon
    LOGGER.info("\n-----")
    LOGGER.info("volume_control_callback control_key: %s event: %s value: %s" % (control_key, event, value))
    command = None
    param = None
    if value == 1:
        command = settings["command_volume_up"]["command"]
        param = settings["command_volume_up"]["param"]
    elif value == -1:
        command = settings["command_volume_down"]["command"]
        param = settings["command_volume_down"]["param"]
    elif event == "set_mute":
        command = settings["command_volume_mute"]["command"]
        param = settings["command_volume_mute"]["param"]
    if not command == None:
        command = '"%s" %s' % (command,param)
        LOGGER.info("running command %s" % (command))
        try:
            subprocess.run(shlex.split(command))
        except:
            pass
    roon.update_volume_control(control_key, 0, False)


def loadSettings():
    global dataFolder
    global dataFile
    global settings
    LOGGER.info("running from %s" % __file__)
    # LOGGER.info(os.environ)
    if ("_" in __file__): # running in temp directory, so not from PyCharm
        dataFolder = os.path.join(os.getenv('APPDATA'), 'pyRoonEGVolume')  #os.path.abspath(os.path.dirname(__file__))
    else:
        dataFolder = os.path.dirname(__file__)
    dataFile = os.path.join(dataFolder , 'settings.dat')
    LOGGER.info("using dataFile: %s" % dataFile)
    if not os.path.isfile(dataFile):
        f = open(dataFile, 'a').close()
    try:
        f = open(dataFile, 'r')
        settings = json.load(f)
    except:
        settings = json.loads('{}')
    f.close()
    return settings

def saveSettings():
    global settings
    data = json.dumps(settings, indent=4)
    if (not data  == '{}') and (os.path.isfile(dataFile)):
        f = open(dataFile, 'w')
        f.write(data)
        f.close()

if __name__ == "__main__":
    main()