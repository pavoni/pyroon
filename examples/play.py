from roonapi import RoonApi

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

server = "192.168.1.160"
target_zone = "Mixing Speakers"
# Can be None if you don't yet have a token
token = open("mytokenfile").read()

roonapi = RoonApi(appinfo, token, server)

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

# save the token for next time
with open("mytokenfile", "w") as f:
    f.write(roonapi.token)
