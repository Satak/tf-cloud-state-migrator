import requests
import hashlib
import base64
from os import environ
import csv
from dataclasses import dataclass

from colorama import init, Fore, Back, Style

init(autoreset=True)


@dataclass
class WorkspaceMigration:
    """Class for migration state."""
    source_org: str
    target_org: str
    workspace_name: str
    source_ws_id: str
    target_ws_id: str
    info: str
    state: str
    migrated: bool

    @staticmethod
    def get_params():
        return list(WorkspaceMigration.__annotations__.keys())


def out_csv(data, file_name="migration.csv"):
    fieldnames = WorkspaceMigration.get_params()
    with open(file_name, 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            writer.writerow(item.__dict__)


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
    return {ws["attributes"]["name"]: {"id": ws["id"], "locked": ws["attributes"]["locked"]} for ws in data}


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


def lock_workspace(workspace_id, base_url, headers, lock_type="lock"):
    api_endpoint = f"/workspaces/{workspace_id}/actions/{lock_type}"
    url = base_url + api_endpoint
    requests.post(url, headers=headers)


def main():
    # $ENV:SOURCE_ORG_NAME = ""
    # $ENV:TARGET_ORG_NAME = ""
    # $ENV:TFE_TOKEN = ""
    unlock_source = False
    lock_source = False
    source_org_name = environ["SOURCE_ORG_NAME"]
    target_org_name = environ["TARGET_ORG_NAME"]
    tfe_token = environ["TFE_TOKEN"]
    base_url = "https://app.terraform.io/api/v2"

    headers = get_headers(tfe_token)

    source_workspaces = get_workspace_ids(
        source_org_name, base_url, headers)

    target_workspaces = get_workspace_ids(
        target_org_name, base_url, headers)

    print('Source organization:', Style.BRIGHT +
          Back.GREEN + Fore.BLACK + source_org_name)
    print('Target organization:', Style.BRIGHT +
          Back.BLUE + Fore.BLACK + target_org_name)

    data = []

    for source_ws_name, source_ws in source_workspaces.items():
        target_ws_id = "NA"
        info = "Migration not started"
        state = "FAILED"
        migrated = False
        source_ws_id = source_ws["id"]

        ws_migration = WorkspaceMigration(
            source_org_name,
            target_org_name,
            source_ws_name,
            source_ws_id,
            target_ws_id,
            info,
            state,
            migrated
        )

        print("\n")
        print(Style.BRIGHT + Back.BLUE + Fore.BLACK + source_ws_name)
        state_data = None

        if source_ws_name in target_workspaces:
            state_data = get_state_payload(source_ws_id, base_url, headers)
        else:
            info = f"Source workspace name not found from target workspaces"

            print(Style.BRIGHT + Back.RED + Fore.BLACK +
                  "STATE MIGRATION FAIL")
            print(info)
            ws_migration.info = info
            data.append(ws_migration)
            continue

        if state_data:
            target_ws = target_workspaces[source_ws_name]
            target_ws_id = target_ws["id"]
            ws_migration.target_ws_id = target_ws_id
            print(Style.BRIGHT + Back.GREEN + Fore.BLACK +
                  "STATE MIGRATION SUCCESS")
            print('Target workstation ID', target_ws_id)

            if not target_ws["locked"]:
                lock_workspace(target_ws_id, base_url, headers)

            post_new_state(target_ws_id, state_data, base_url, headers)
            ws_migration.info = "Migration OK"
            ws_migration.state = "MIGRATED"
            ws_migration.migrated = True

            if lock_source:
                lock_workspace(source_ws_id, base_url, headers)

            if not target_ws["locked"]:
                lock_workspace(target_ws_id, base_url, headers, "unlock")
        else:
            info = f"Source workspace does not have any state"
            print(Style.BRIGHT + Back.YELLOW + Fore.BLACK +
                  "STATE MIGRATION SKIPPED")
            print(info)
            ws_migration.info = info
            ws_migration.state = "SKIPPED"
            ws_migration.migrated = False
        data.append(ws_migration)

        if unlock_source:
            lock_workspace(source_ws_id, base_url, headers, "unlock")

    out_csv(data)


if __name__ == "__main__":
    main()
