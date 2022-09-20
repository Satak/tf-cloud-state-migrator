from os import environ
import requests


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


def lock_workspace(workspace_id, base_url, headers, lock_type="lock"):
    api_endpoint = f"/workspaces/{workspace_id}/actions/{lock_type}"
    url = base_url + api_endpoint
    requests.post(url, headers=headers)


def main():
    # $ENV:ORG_NAME = ""
    # $ENV:TFE_TOKEN = ""
    lock_type = 'lock'  # unlock
    org_name = environ["ORG_NAME"]
    tfe_token = environ["TFE_TOKEN"]
    base_url = "https://app.terraform.io/api/v2"

    headers = get_headers(tfe_token)

    workspaces = get_workspace_ids(
        org_name, base_url, headers)

    for ws_name, ws in workspaces.items():
        ws_id = ws["id"]
        lock_workspace(ws_id, base_url, headers, lock_type)
        print('Workspace:', ws_name, 'id:', ws_id, 'lock_type', lock_type)


if __name__ == "__main__":
    main()
