import api4jenkins
import json
import re
from typing import Dict,Any
from datetime import datetime

secrets_stream = open("secrets.json")
secrets = json.load(secrets_stream)
secrets_stream.close()

server = api4jenkins.Jenkins("http://" + secrets["url"], auth=(secrets["user"], secrets["pword"]))

ip_replacement = r"\d+\.\d+\.\d+\.\d+"
build_name_parser = r".*(" + secrets["project_prefix"].upper() + "[\w-]*) \@(\d+).*" # parses "Health Check of PP-trunk-blah-poo @23123 (Build Node Name)"

def get_jenkins_state() -> Dict[str,Any]:
    """generates a dict representing the current state of jenkins. should match tuftyclient's jenkinsdisplay arguments

    Returns:
        Dict[str,Any]: whatever the current blob of jenkinsdisplay.show is 
    """
    machines = []
    machine_names = [f"{secrets['project_prefix'].upper()} Node {i+1}" for i in range(3)]
    for node in machine_names:
        node_info = server.nodes.get(node)
        machine_state = {
            "machine": "N" + node[-1], # to keep things compact, we'll only send "N1"
            "is_online": node_info.offline == False,
        }
        for build_info in node_info.iter_builds():
            build_info.url = re.sub(ip_replacement, secrets["url"], build_info.url)
            display_name = build_info.display_name
            
            # do some cleanup so display_name isn't too long
            build_parts = re.match(build_name_parser, display_name)
            if build_parts is None:
                # we can't identify this build, do the full name
                machine_state["build"] = display_name
                machine_state["changelist"] = -1
            else:
                prefix = "Health: " if "Health" in display_name \
                    else "Deploy: " if "Deploy" in display_name \
                    else ""
                machine_state["build"] = prefix + build_parts.group(1)
                machine_state["changelist"] = int(build_parts.group(2))
            
            start_timestamp = build_info.timestamp/1000 ## from ms to secs
            start_time = datetime.fromtimestamp(start_timestamp)
            machine_state["duration"] = int((datetime.now() - start_time).total_seconds())
            
            machine_state["step"] = "todo"
        machines.append(machine_state)
    
    return {"machines": machines}
            
if __name__ == "__main__":
    print(get_jenkins_state())