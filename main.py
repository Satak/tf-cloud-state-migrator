import requests
import hashlib
import base64
from os import environ

source_org = ""
target_org = ""

source_workspace_id = environ["SOURCE_WS_ID"]
target_workspace_id = ""

headers = {
    'Authorization': f'Bearer {environ["SOURCE_TOKEN"]}',
    'Content-Type': 'application/json'
}

base_url = "https://app.terraform.io/api/v2"
api_endpoint = f"/workspaces/{source_workspace_id}/current-state-version"

source_full_url = base_url + api_endpoint

current_source_version = requests.get(
    source_full_url, params=None, headers=headers).json()["data"]

source_state_url = current_source_version["attributes"]["hosted-state-download-url"]

res = requests.get(
    source_state_url, params=None, headers=headers)
content = res.content

source_pull_state = res.json()

source_state_serial = source_pull_state["serial"]
source_state_lineage = source_pull_state["lineage"]

source_state_hash = hashlib.md5()
source_state_hash.update(content)
source_state_md5 = source_state_hash.hexdigest()

source_state_b64 = base64.b64encode(content).decode("utf-8")

# Build the new state payload
create_state_version_payload = {
    "data": {
        "type": "state-versions",
        "attributes": {
            "serial": source_state_serial,
            "md5": source_state_md5,
            "lineage": source_state_lineage,
            "state": source_state_b64
        }
    }
}

print(create_state_version_payload)
