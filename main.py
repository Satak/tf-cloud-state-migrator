import requests
import hashlib
import base64
from os import environ

from colorama import init, Fore, Back, Style

init(autoreset=True)


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.api+json"
    }


def get_workspace_ids(org_name, base_url, headers):
    api_endpoint = f"/organizations/{org_name}/workspaces"
    url = base_url + api_endpoint

    data = requests.get(
        url, params=None, headers=headers).json()["data"]
    return {ws["attributes"]["name"]: ws["id"] for ws in data}


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
    res = requests.post(url, json=payload, headers=headers)


def lock_workspace(workspace_id, base_url, headers, lock_type="lock"):
    api_endpoint = f"/workspaces/{workspace_id}/actions/{lock_type}"
    url = base_url + api_endpoint
    requests.post(url, headers=headers)


def main():
    # $ENV:TARGET_ORG_NAME = ""
    source_org_name = environ["SOURCE_ORG_NAME"]
    target_org_name = environ["TARGET_ORG_NAME"]
    tfe_token = environ["TFE_TOKEN"]
    base_url = "https://app.terraform.io/api/v2"

    headers = get_headers(tfe_token)

    source_ws_ids = get_workspace_ids(
        source_org_name, base_url, headers)

    target_ws_ids = get_workspace_ids(
        target_org_name, base_url, headers)

    for source_ws_name, source_ws_id in source_ws_ids.items():
        print("\n")
        print(Style.BRIGHT + Back.BLUE + Fore.BLACK + source_ws_name)
        state_data = None

        if source_ws_name in target_ws_ids:
            state_data = get_state_payload(source_ws_id, base_url, headers)
        else:
            print(Style.BRIGHT + Back.RED + Fore.BLACK +
                  "STATE MIGRATION FAIL")
            print("Source workspace name:", source_ws_name,
                  "not found from target workspaces!")

        if state_data:
            target_ws_id = target_ws_ids[source_ws_name]
            print(Style.BRIGHT + Back.GREEN + Fore.BLACK +
                  "STATE MIGRATION SUCCESS")
            print('Target workstation ID', target_ws_id)

            lock_workspace(target_ws_id, base_url, headers)
            post_new_state(target_ws_id, state_data, base_url, headers)
            lock_workspace(target_ws_id, base_url, headers, "unlock")


if __name__ == "__main__":
    main()
