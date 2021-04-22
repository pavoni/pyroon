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
    group_main_zone = roonapi.group_main_zone(output_id)
    group_main_zone_name = roonapi.group_main_zone_name(output_id)
    if group_main_zone is None:
        group_main_zone_name_grouped = ""
    else:
        group_main_zone_name_grouped = zones[group_main_zone]["display_name"]
    print(
        display_name,
        "grouped?",
        is_grouped,
        "is_main?",
        is_group_main,
        "main zone:",
        group_main_zone_name,
        "group zone name:",
        group_main_zone_name_grouped,
    )

# save the token for next time
with open("mytokenfile", "w") as f:
    f.write(roonapi.token)
