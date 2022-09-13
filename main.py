import requests
import hashlib
import base64
from os import environ

state_hash = hashlib.md5()


def get_workspace_ids(org_name, base_url, headers):
    ws_api_endpoint = f"/organizations/{org_name}/workspaces"
    url = base_url + ws_api_endpoint

    ws_data = requests.get(
        url, params=None, headers=headers).json()["data"]
    return {ws["attributes"]["name"]: ws["id"] for ws in ws_data}


def get_state_payload(workspace_id, base_url, headers):
    ws_state_api_endpoint = f"/workspaces/{workspace_id}/current-state-version"

    ws_url = base_url + ws_state_api_endpoint

    ws_res = requests.get(ws_url, params=None, headers=headers)
    print(ws_res.status_code)

    if ws_res.status_code != 200:
        return

    state_url = ws_res.json(
    )["data"]["attributes"]["hosted-state-download-url"]

    state_res = requests.get(
        state_url, params=None, headers=headers)

    state_raw_content = state_res.content
    state_dict = state_res.json()

    state_hash.update(state_raw_content)
    state_md5 = state_hash.hexdigest()
    state_b64 = base64.b64encode(
        state_raw_content).decode("utf-8")

    # Build the new state payload
    return {
        "data": {
            "type": "state-versions",
            "attributes": {
                "serial": state_dict["serial"],
                "md5": state_md5,
                "lineage": state_dict["lineage"],
                "state": state_b64
            }
        }
    }


def main():
    source_workspace_id = environ["SOURCE_WS_ID"]
    source_org_name = environ["SOURCE_ORG_NAME"]
    source_token = environ["SOURCE_TOKEN"]

    headers = {
        "Authorization": f"Bearer {source_token}",
        "Content-Type": "application/json"
    }

    base_url = "https://app.terraform.io/api/v2"

    source_ws_ids = get_workspace_ids(source_org_name, base_url, headers)

    for ws_name, ws_id in source_ws_ids.items():
        print(ws_name)
        d = get_state_payload(ws_id, base_url, headers)
        print(d)


if __name__ == "__main__":
    main()
