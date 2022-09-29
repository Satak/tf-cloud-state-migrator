import requests
import hashlib
import base64
from os import environ


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.api+json"
    }


def get_state_payload(workspace_id, base_url, headers):
    api_endpoint = f"/workspaces/{workspace_id}/current-state-version"
    url = base_url + api_endpoint

    res = requests.get(url, params=None, headers=headers)

    if res.status_code != 200:
        return

    state_url = res.json(
    )["data"]["attributes"]["hosted-state-download-url"]

    state_res = requests.get(
        state_url, params=None, headers=headers)

    state_raw_content = state_res.content
    state_dict = state_res.json()

    state_hash = hashlib.md5()

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


def post_new_state(workspace_id, payload, base_url, headers):
    api_endpoint = f"/workspaces/{workspace_id}/state-versions"
    url = base_url + api_endpoint
    return requests.post(url, json=payload, headers=headers)


def main():
    # $ENV:SOURCE_WS_ID = ""
    # $ENV:TARGET_WS_ID = ""
    # $ENV:TFE_TOKEN = ""

    source_ws_id = environ["SOURCE_WS_ID"]
    target_ws_id = environ["TARGET_WS_ID"]
    tfe_token = environ["TFE_TOKEN"]

    base_url = "https://app.terraform.io/api/v2"

    headers = get_headers(tfe_token)

    state_data = get_state_payload(source_ws_id, base_url, headers)
    res = post_new_state(target_ws_id, state_data, base_url, headers)
    print(res.json())


if __name__ == "__main__":
    main()
