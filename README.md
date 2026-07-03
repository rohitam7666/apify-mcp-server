# APIFY_MCP — Apify Actor Runtime for AI Agents

Run any Apify Actor from inside your AI agent. Access 1,500+ pre-built cloud scrapers via MCP.

## Setup

```bash
pip install -r APIFY_requirements.txt

# Set your Apify API token
$env:APIFY_TOKEN = "your_apify_token_here"

# Run the MCP server
python APIFY_MCP.py
```

Get your token at: https://console.apify.com/account/integrations

## Tools

| Tool | Description | Use Case |
|---|---|---|
| `run_actor` | Launch any Actor | Fire-and-forget scraping |
| `get_run_status` | Poll run status | Async pipeline monitoring |
| `get_dataset_items` | Fetch scraped data | Retrieve results after run |
| `run_actor_and_get_results` | All-in-one scrape | Quick data extraction |
| `search_apify_store` | Search 1500+ Actors | Discover scrapers |
| `list_my_actors` | List your Actors | Manage published tools |
| `list_recent_runs` | Recent run history | Cost monitoring |
| `save_to_kv_store` | Store data in cloud | Agent state persistence |
| `read_from_kv_store` | Retrieve stored data | Read cached results |
| `get_account_stats` | Account usage | Track compute costs |

## Example: Scrape Google Search Results

```python
result = run_actor_and_get_results(
    actor_id="apify/google-search-scraper",
    actor_input={
        "queries": "best MCP tools 2026",
        "maxPagesPerQuery": 1,
        "resultsPerPage": 10
    },
    timeout_secs=60
)
print(result["results"])
```

## Example: Scrape YouTube Transcripts

```python
result = run_actor_and_get_results(
    actor_id="streamers/youtube-transcript-scraper",
    actor_input={"videoUrls": ["https://youtube.com/watch?v=dQw4w9WgXcQ"]},
    timeout_secs=30
)
```

## Revenue Model
- This MCP charges **$0.05/call** via the x402 A2A payment protocol
- Apify's own compute is billed to your Apify account (~$0.003/minute of compute)
- Net margin: ~90% on each call

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `APIFY_TOKEN` | ✅ Yes | Your Apify API token |
| `A2A_WALLET` | Optional | Treasury wallet for payment logging |

---
*Built by the Gemini Power Agent — Turning Code into Capital.*
