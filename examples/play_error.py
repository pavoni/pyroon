from roonapi import RoonApi, RoonDiscovery

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

target_zone = "Study"

try:
    core_id = open("my_core_id_file").read()
    token = open("my_token_file").read()
except OSError:
    print("Please authorise first using discovery.py")
    exit()

discover = RoonDiscovery(core_id)
server = discover.first()
discover.stop()

roonapi = RoonApi(appinfo, token, server[0], server[1], True)

# get target zone output_id
zones = roonapi.zones
output_id = [
    output["zone_id"]
    for output in zones.values()
    if output["display_name"] == target_zone
][0]
print("OUTPUT ID", output_id)

# Examples of using play_media

print("PLAY Something unplayable - should give error")
items = roonapi.play_media(output_id, ["Qobuz", "My Qobuz", "Favorite Albums"])

print("PLAY Something playable - this should work")
items = roonapi.play_media(
    output_id, ["Qobuz", "My Qobuz", "Favorite Albums", "Umiera Piekno"]
)
