from roonapi import RoonApi

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

host = "192.168.3.61"
port = 9330
target_zone = "Mixing Speakers"
# Can be None if you don't yet have a token
token = open("mytokenfile").read()

roonapi = RoonApi(appinfo, token, host, port)

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
    output_id, ["Qobuz", "My Qobuz", "Favorite Albums", "Grover Live"]
)

# save the token for next time
with open("mytokenfile", "w") as f:
    f.write(roonapi.token)
