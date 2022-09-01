import api4jenkins
import json
import re

secrets_stream = open("secrets.json")
secrets = json.load(secrets_stream)
secrets_stream.close()

server = api4jenkins.Jenkins("http://" + secrets["url"], auth=(secrets["user"], secrets["pword"]))

ip_replacement = r"\d+\.\d+\.\d+\.\d+"

for node in ["PX Node 1", "PX Node 2", "PX Node 3"]:
    node_info = server.nodes.get(node)
    print(node_info)
    for build_info in node_info.iter_builds():
        build_info.url = re.sub(ip_replacement, secrets["url"], build_info.url)
        print(build_info.display_name)