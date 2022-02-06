from roonapi import RoonApi, RoonDiscovery

appinfo = {
    "extension_id": "python_roon_test",
    "display_name": "Python library for Roon",
    "display_version": "1.0.0",
    "publisher": "gregd",
    "email": "mygreat@emailaddress.com",
}

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
