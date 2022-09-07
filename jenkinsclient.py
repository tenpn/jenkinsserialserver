import api4jenkins
import json
import re
from typing import Dict,Any,Tuple,List
from datetime import datetime

secrets_stream = open("secrets.json")
secrets = json.load(secrets_stream)
secrets_stream.close()

server = api4jenkins.Jenkins("http://" + secrets["url"], auth=(secrets["user"], secrets["pword"]))

ip_replacement = r"\d+\.\d+\.\d+\.\d+"
build_name_parser = r".*(" + secrets["project_prefix"].upper() + "[\w-]*) \@(\d+).*" # parses "Health Check of PP-trunk-blah-poo @23123 (Build Node Name)"

def find_active_stage_in(wfapi_desc: dict) -> str:
    """given some jenkins state, finds the active pipeline stage

    Args:
        wfapi_desc (dict): the result from wfapi/describe on the specific job

    Returns:
        str: the name of the active stage, or None if can't be found
    """
    if "stages" not in wfapi_desc:
        return None
    for stage in wfapi_desc["stages"]:
        if stage["status"] == "IN_PROGRESS":
            return stage["name"]
    return None

def get_friendly_build_name(build_full_name: str) -> Tuple[str, int]:
    """turns a full name into something more friendly for tufty

    Args:
        build_full_name (str): the build name as jenkins knows it

    Returns:
        Tuple[str, int]: (friendlier build name, changelist). changelist is -1 if can't be found.
    """
    build_parts = re.match(build_name_parser, build_full_name)
    if build_parts is None:
        return (build_full_name, -1)
    
    prefix = "Health: " if "Health" in build_full_name \
        else "Deploy: " if "Deploy" in build_full_name \
        else ""
    # (the project prefix is too repetitive)
    friendly_name = prefix + build_parts.group(1).replace(secrets["project_prefix"].upper()+"-", "")
    cl = int(build_parts.group(2))
    return (friendly_name, cl)

def get_node_state(node_name: str) -> Dict[str,Any]:
    """produces a json-compatible dict about this node, compatible with tuftyclient's jenkinsdisplay arguments

    Args:
        node_name (str): the node to invesigate

    Returns:
        Dict[str,Any]: node info
    """
    node_info = server.nodes.get(node_name)        
    machine_state = {
        "machine": "N" + node_name[-1], # to keep things compact, we'll only send "N1"
        "is_online": node_info.offline == False,
    }
    for build_info in node_info.iter_builds():
        build_info.url = re.sub(ip_replacement, secrets["url"], build_info.url)
        display_name = build_info.display_name
        
        # do some cleanup so display_name isn't too long
        (build_friendly_name, build_cl) = get_friendly_build_name(display_name)
        machine_state["build"] = build_friendly_name
        if build_cl < 0:
            # we can't identify this build, no steps
            machine_state["step"] = ""
        else:
            machine_state["changelist"] = build_cl
            
            # need to ask again for stage info 
            stage_desc = build_info.handle_req('GET', 'wfapi/describe').json()
            active_stage = find_active_stage_in(stage_desc)
            machine_state["step"] = active_stage if active_stage is not None else ""
        
        start_timestamp = build_info.timestamp/1000 ## from ms to secs
        start_time = datetime.fromtimestamp(start_timestamp)
        machine_state["duration"] = int((datetime.now() - start_time).total_seconds())
    return machine_state

def get_most_recent_job(builds: List[Any]) -> Dict[str,Any]:
    """given a list of jobs, find the most recent

    Args:
        jobs (List[Any]): json-dict from jenkins, containing at least timestamp, duration and displayName

    Returns:
        Dict[str,Any]: the most recent job, built for tuftyclient
    """
    most_recent_interesting_build = None
    most_recent_interesting_timestamp = 0
    for build in builds:
        end_timestamp = build["timestamp"] + build["duration"]
        if end_timestamp < most_recent_interesting_timestamp:
            continue
        (build_name, build_cl) = get_friendly_build_name(build["displayName"])
        if build_cl <= 0:
            # this isn't a real build? 
            continue 
        most_recent_interesting_build = {
            "build": build_name,
            "changelist": build_cl,
            "age": int((datetime.now() - datetime.fromtimestamp(end_timestamp/1000)).total_seconds()),
            "result": build["result"],
        }
        most_recent_interesting_timestamp = end_timestamp
        
    return most_recent_interesting_build

def get_jenkins_interesting_completed_builds() -> Tuple[Dict[str,Any], Dict[str,Any]]:
    """gets the most Interesting recent completed build

    Returns:
        (Dict[str,Any], Dict[str,Any]): tuftydisplay-compatible json-compatible objects, one for most recent failure and one for most recent success. one or more might be None
    """
    # the switching IP addresses make this hard to get through api4jenkins
    jobs_status = \
        server.handle_req("GET", "view/ProjectX/api/json?tree=jobs[name,lastCompletedBuild[displayName,result,timestamp,duration]]").json()["jobs"]
    completed_builds = [job["lastCompletedBuild"] for job in jobs_status]
        
    most_recent_success = get_most_recent_job([success_build for success_build in completed_builds if success_build["result"] == "SUCCESS"])
    most_recent_failure = get_most_recent_job([success_build for success_build in completed_builds if success_build["result"] != "SUCCESS"])
    return (most_recent_failure, most_recent_success)

def get_jenkins_state() -> Dict[str,Any]:
    """generates a dict representing the current state of jenkins. should match tuftyclient's jenkinsdisplay arguments

    Returns:
        Dict[str,Any]: whatever the current blob of jenkinsdisplay.show is 
    """
    machines = []
    machine_names = [f"{secrets['project_prefix'].upper()} Node {i+1}" for i in range(3)]
    for node in machine_names:
        machine_state = get_node_state(node)
        machines.append(machine_state)
        
    (recent_failure, recent_success) = get_jenkins_interesting_completed_builds()
    
    results = { "machines": machines }
    if recent_failure is not None:
        results["recent_failure"] = recent_failure
    if recent_success is not None:
        results["recent_success"] = recent_success
    return results
            
if __name__ == "__main__":
    print(get_jenkins_state())
    