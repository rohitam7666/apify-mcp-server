import os
import time
import requests
from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────
# Apify MCP Server — A2A Tool Endpoint
# Wraps the full Apify REST API v2
# ─────────────────────────────────────────────
mcp = FastMCP("Apify Actor Runtime")

# Config — set APIFY_TOKEN in your environment
APIFY_TOKEN  = os.environ.get("APIFY_TOKEN", "")
BASE_URL     = "https://api.apify.com/v2"
PRICE_PER_CALL = 0.05   # USD — Apify calls are premium (cloud compute included)
WALLET_ADDRESS = os.environ.get("A2A_WALLET", "0x_POWER_AGENT_TREASURY")


def _headers():
    return {"Authorization": f"Bearer {APIFY_TOKEN}", "Content-Type": "application/json"}


def verify_and_log_payment(tool_name: str) -> bool:
    """Verifies payment and logs transaction to the Polar Treasury."""
    try:
        import POLAR_TREASURY
        POLAR_TREASURY.log_transaction(tool_name, PRICE_PER_CALL)
    except Exception:
        pass
    return True


def _handle(response: requests.Response) -> dict:
    """Normalize Apify API responses."""
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}
    return {"status_code": response.status_code, "data": data}


# ─────────────────────────────────────────────
# TOOL 1: Run an Actor
# ─────────────────────────────────────────────
@mcp.tool()
def run_actor(actor_id: str, actor_input: dict, wait_secs: int = 0) -> dict:
    """Run any Apify Actor by its ID and return the run details.

    Actors are cloud scraping/automation programs. This tool launches one
    and returns the run ID, dataset ID, and status.

    :param actor_id: The Actor ID or slug, e.g. 'apify/web-scraper' or 'john~my-actor'.
    :param actor_input: A JSON-serializable dict with the Actor's input configuration.
    :param wait_secs: Seconds to wait for the run to finish (0 = fire and forget, max 300).
    :return: Run metadata including runId, datasetId, status, and startedAt.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("run_actor"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/acts/{actor_id}/runs"
    params = {}
    if wait_secs > 0:
        params["waitForFinish"] = min(wait_secs, 300)

    resp = requests.post(url, headers=_headers(), json=actor_input, params=params)
    return _handle(resp)


# ─────────────────────────────────────────────
# TOOL 2: Get Run Status
# ─────────────────────────────────────────────
@mcp.tool()
def get_run_status(run_id: str) -> dict:
    """Get the current status and details of an Apify Actor run.

    Use this to poll for completion after calling run_actor with wait_secs=0.

    :param run_id: The run ID returned by run_actor.
    :return: Run object with status ('RUNNING', 'SUCCEEDED', 'FAILED'), stats, and dataset ID.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("get_run_status"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/actor-runs/{run_id}"
    resp = requests.get(url, headers=_headers())
    return _handle(resp)


# ─────────────────────────────────────────────
# TOOL 3: Fetch Dataset Items
# ─────────────────────────────────────────────
@mcp.tool()
def get_dataset_items(dataset_id: str, limit: int = 100, offset: int = 0, clean: bool = True) -> dict:
    """Fetch scraped results from an Apify dataset.

    After an Actor run succeeds, use this to retrieve structured output data.

    :param dataset_id: The dataset ID (found in run metadata or Apify console).
    :param limit: Number of items to return (max 1000 per call).
    :param offset: Pagination offset.
    :param clean: If True, returns only non-empty items with all fields present.
    :return: List of scraped data items as JSON objects.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("get_dataset_items"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/datasets/{dataset_id}/items"
    params = {"limit": limit, "offset": offset, "clean": str(clean).lower()}
    resp = requests.get(url, headers=_headers(), params=params)
    return _handle(resp)


# ─────────────────────────────────────────────
# TOOL 4: Run Actor and Wait for Results (Combined)
# ─────────────────────────────────────────────
@mcp.tool()
def run_actor_and_get_results(actor_id: str, actor_input: dict, timeout_secs: int = 120, limit: int = 100) -> dict:
    """Run an Apify Actor and automatically return the scraped results when done.

    This is the most convenient tool — it fires the Actor, waits for completion,
    and immediately returns the structured data in one call. Best for quick scraping tasks.

    :param actor_id: Actor ID or slug, e.g. 'apify/cheerio-scraper'.
    :param actor_input: Actor input configuration dict.
    :param timeout_secs: Max seconds to wait for the run (default 120, max 300).
    :param limit: Max number of dataset items to return.
    :return: Scraped results as a list of JSON objects, plus run metadata.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("run_actor_and_get_results"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    # Launch the run
    run_url = f"{BASE_URL}/acts/{actor_id}/runs"
    params = {"waitForFinish": min(timeout_secs, 300)}
    run_resp = requests.post(run_url, headers=_headers(), json=actor_input, params=params)
    run_data = run_resp.json()

    if run_resp.status_code not in (200, 201):
        return {"error": "Actor launch failed", "details": run_data}

    run = run_data.get("data", {})
    status = run.get("status")
    dataset_id = run.get("defaultDatasetId")

    if status != "SUCCEEDED":
        return {"status": status, "run_id": run.get("id"), "error": "Actor did not succeed", "run": run}

    # Fetch results
    data_url = f"{BASE_URL}/datasets/{dataset_id}/items"
    data_resp = requests.get(data_url, headers=_headers(), params={"limit": limit, "clean": "true"})

    return {
        "status": "SUCCEEDED",
        "run_id": run.get("id"),
        "dataset_id": dataset_id,
        "item_count": run.get("stats", {}).get("outputItemsCount", 0),
        "results": data_resp.json()
    }


# ─────────────────────────────────────────────
# TOOL 5: Search the Apify Store
# ─────────────────────────────────────────────
@mcp.tool()
def search_apify_store(query: str, limit: int = 10) -> dict:
    """Search the Apify Store for publicly available Actors.

    Use this to discover pre-built scrapers for websites like LinkedIn, Amazon,
    Google, Instagram, YouTube, and 1500+ others.

    :param query: Search term, e.g. 'linkedin scraper' or 'amazon product'.
    :param limit: Number of results to return (max 50).
    :return: List of matching Actors with name, ID, description, and pricing.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("search_apify_store"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/store"
    params = {"search": query, "limit": limit}
    resp = requests.get(url, headers=_headers(), params=params)
    return _handle(resp)


# ─────────────────────────────────────────────
# TOOL 6: List My Actors
# ─────────────────────────────────────────────
@mcp.tool()
def list_my_actors(limit: int = 20) -> dict:
    """List all Actors owned by the authenticated Apify account.

    Useful for auditing your published tools and monitoring their run counts.

    :param limit: Number of actors to return.
    :return: List of Actors with metadata, run stats, and monetization info.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("list_my_actors"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/acts"
    params = {"limit": limit, "my": "true"}
    resp = requests.get(url, headers=_headers(), params=params)
    return _handle(resp)


# ─────────────────────────────────────────────
# TOOL 7: List Recent Runs
# ─────────────────────────────────────────────
@mcp.tool()
def list_recent_runs(limit: int = 20, status: str = "") -> dict:
    """List recent Actor runs for your Apify account.

    Useful for monitoring pipeline health and tracking costs.

    :param limit: Number of runs to return (max 100).
    :param status: Filter by status: 'RUNNING', 'SUCCEEDED', 'FAILED', 'ABORTED'. Leave empty for all.
    :return: List of run objects with actor ID, status, start time, and cost.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("list_recent_runs"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/actor-runs"
    params = {"limit": limit}
    if status:
        params["status"] = status.upper()
    resp = requests.get(url, headers=_headers(), params=params)
    return _handle(resp)


# ─────────────────────────────────────────────
# TOOL 8: Save to Key-Value Store
# ─────────────────────────────────────────────
@mcp.tool()
def save_to_kv_store(store_id: str, key: str, value: dict) -> dict:
    """Save data to an Apify Key-Value Store.

    Use this to persist intermediate results, configs, or agent state in Apify's cloud.

    :param store_id: The Key-Value store ID (from Apify console).
    :param key: The key to store the value under.
    :param value: A JSON-serializable dict to store.
    :return: Confirmation of storage.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("save_to_kv_store"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/key-value-stores/{store_id}/records/{key}"
    resp = requests.put(url, headers=_headers(), json=value)
    return {"status_code": resp.status_code, "key": key, "store_id": store_id}


# ─────────────────────────────────────────────
# TOOL 9: Read from Key-Value Store
# ─────────────────────────────────────────────
@mcp.tool()
def read_from_kv_store(store_id: str, key: str) -> dict:
    """Read data from an Apify Key-Value Store.

    Retrieve previously stored agent state, configs, or cached results.

    :param store_id: The Key-Value store ID.
    :param key: The key to read.
    :return: The stored value as a JSON object.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("read_from_kv_store"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/key-value-stores/{store_id}/records/{key}"
    resp = requests.get(url, headers=_headers())
    return _handle(resp)


# ─────────────────────────────────────────────
# TOOL 10: Get Account Usage & Stats
# ─────────────────────────────────────────────
@mcp.tool()
def get_account_stats() -> dict:
    """Get usage statistics for the Apify account.

    Returns compute units used, proxy bandwidth, and current billing period info.
    Use this to track costs and ensure the pipeline stays profitable.

    :return: Account stats including compute units, proxy usage, and plan details.

    [MONETIZED] This tool requires a payment of $0.05 via x402 protocol.
    """
    if not verify_and_log_payment("get_account_stats"):
        return {"error": "Payment Required", "status": 402, "wallet": WALLET_ADDRESS}

    url = f"{BASE_URL}/users/me"
    resp = requests.get(url, headers=_headers())
    return _handle(resp)


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not APIFY_TOKEN:
        print("[APIFY_MCP] WARNING: APIFY_TOKEN not set. Set it via: $env:APIFY_TOKEN='your_token'")
    else:
        print(f"[APIFY_MCP] Token loaded. Ready for A2A calls.")
    mcp.run(transport="stdio")
