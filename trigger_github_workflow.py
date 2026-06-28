import os, sys, re, time, requests

def main():
    # Read GH_TOKEN from secrets.sh
    secrets_path = r"c:\Users\elaroos\opencode\telegramdownload\tv-guide\secrets.sh"
    gh_token = None
    with open(secrets_path, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'GH_TOKEN="([^"]+)"', content)
        if match:
            gh_token = match.group(1)
            
    if not gh_token:
        print("[ERROR] GH_TOKEN not found in secrets.sh")
        sys.exit(1)
        
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Trigger dispatch
    url_dispatch = "https://api.github.com/repos/elaroos/tv-guide/actions/workflows/generate.yml/dispatches"
    print("Triggering GitHub Actions workflow...")
    resp = requests.post(url_dispatch, headers=headers, json={"ref": "main"})
    if resp.status_code == 204:
        print("Workflow triggered successfully!")
    else:
        print(f"[ERROR] Failed to trigger workflow: HTTP {resp.status_code}\n{resp.text}")
        sys.exit(1)
        
    # Wait for the run to show up
    print("Waiting for run to start...")
    time.sleep(5)
    
    url_runs = "https://api.github.com/repos/elaroos/tv-guide/actions/runs?event=workflow_dispatch&branch=main&per_page=1"
    run_id = None
    for _ in range(5):
        resp = requests.get(url_runs, headers=headers)
        if resp.status_code == 200:
            runs = resp.json().get("workflow_runs", [])
            if runs:
                # Make sure the run started recently (within 2 minutes)
                created_at = runs[0].get("created_at")
                run_id = runs[0]["id"]
                print(f"Found run ID: {run_id}")
                break
        time.sleep(2)
        
    if not run_id:
        print("[ERROR] Could not find triggered run")
        sys.exit(1)
        
    # Poll status
    print("Polling status...")
    last_status = None
    while True:
        url_run_detail = f"https://api.github.com/repos/elaroos/tv-guide/actions/runs/{run_id}"
        resp = requests.get(url_run_detail, headers=headers)
        if resp.status_code == 200:
            run_data = resp.json()
            status = run_data["status"]
            conclusion = run_data.get("conclusion")
            if status != last_status:
                print(f"Status: {status} (Conclusion: {conclusion})")
                last_status = status
            if status == "completed":
                print(f"Completed with conclusion: {conclusion}")
                if conclusion == "success":
                    print("SUCCESS! EPG and Playlist generated and deployed.")
                else:
                    print("FAILED! Check the workflow logs on GitHub.")
                break
        time.sleep(10)

if __name__ == "__main__":
    main()
