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
print("RADIO")
items = roonapi.play_media(output_id, ["My Live Radio", "BBC Radio 4"])

print("SINGLE ARTIST")
items = roonapi.play_media(output_id, ["Library", "Artists", "Neil Young"])

print("SINGLE ARTIST ALBUM")
items = roonapi.play_media(
    output_id, ["Library", "Artists", "Neil Young", "After The Goldrush"]
)

print("PLAY SINGLE ARTIST ALBUM - use Queue")
items = roonapi.play_media(
    output_id, ["Library", "Artists", "Neil Young", "Harvest"], "Queue"
)

print("PLAY SUB GENRE")
items = roonapi.play_media(output_id, ["Genres", "Jazz", "Cool"])

print("TAG")
items = roonapi.play_media(output_id, ["Library", "Tags", "Mix"])
