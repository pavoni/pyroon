from roonapi import RoonApi

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

# Can be None if you don't yet have a token
token = open("mytokenfile").read()
# token= None


# Take a look at examples/discovery if you want to use discovery.
server = "192.168.3.60"

roonapi = RoonApi(appinfo, token, server)

# get all zones (as dict)
zones = roonapi.zones
outputs = roonapi.outputs

for (k, v) in outputs.items():
    zone_id = v["zone_id"]
    output_id = k
    display_name = v["display_name"]
    is_group_main = roonapi.is_group_main(output_id)
    is_grouped = roonapi.is_grouped(output_id)
    grouped_zone_names = roonapi.grouped_zone_names(output_id)
    print(
        display_name,
        "grouped?",
        is_grouped,
        "is_main?",
        is_group_main,
        "grouped_zone_names:",
        grouped_zone_names,
    )

# save the token for next time
with open("mytokenfile", "w") as f:
    f.write(roonapi.token)
