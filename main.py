import os
import pandas as pd
from huggingface_hub import HfApi
from notion_client import Client
from notion_client.helpers import extract_notion_id, iterate_paginated_api
from dotenv import load_dotenv

load_dotenv()

# Clean ID and Initialize
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
notion = Client(auth=NOTION_TOKEN)
hf_api = HfApi()


def _normalize_notion_id(value):
    parsed = extract_notion_id(value or "")
    if not parsed:
        raise ValueError("Invalid Notion ID/URL. Please provide a valid UUID or Notion URL.")
    return parsed


def discover_shared_data_sources(limit=20):
    """Return data source IDs shared with this integration."""
    response = notion.search(
        filter={"property": "object", "value": "data_source"},
        page_size=limit,
    )
    return [
        item.get("id")
        for item in response.get("results", [])
        if item.get("object") == "data_source" and item.get("id")
    ]


def resolve_data_source_id():
    """Resolve the target data source ID for notion-client>=3.0.0."""
    data_source_candidate = os.getenv("NOTION_DATA_SOURCE_ID", "").strip()
    database_candidate = os.getenv("NOTION_DATABASE_ID", "").strip()

    if data_source_candidate:
        data_source_id = _normalize_notion_id(data_source_candidate)
        notion.data_sources.retrieve(data_source_id=data_source_id)
        return data_source_id

    if not database_candidate:
        raise ValueError("Set NOTION_DATA_SOURCE_ID (preferred) or NOTION_DATABASE_ID in .env.")

    database_id = _normalize_notion_id(database_candidate)

    # If user pasted a data source ID into NOTION_DATABASE_ID, accept it.
    try:
        notion.data_sources.retrieve(data_source_id=database_id)
        return database_id
    except Exception:
        pass

    try:
        db = notion.databases.retrieve(database_id=database_id)
        data_sources = db.get("data_sources", [])
        if data_sources:
            return data_sources[0]["id"]
    except Exception:
        pass

    # Last fallback: auto-detect among objects shared with this integration.
    shared_sources = discover_shared_data_sources()
    if len(shared_sources) == 1:
        print("ℹ️ Auto-selected shared Notion data source.")
        return shared_sources[0]
    if len(shared_sources) > 1:
        raise ValueError(
            "Multiple shared data sources found. Set NOTION_DATA_SOURCE_ID explicitly in .env."
        )
    raise ValueError(
        "Could not resolve a valid data source. Share your target database with the integration and set NOTION_DATA_SOURCE_ID."
    )

def get_existing_ids(data_source_id):
    """Fetch existing Model IDs from a Notion data source."""
    try:
        seen = set()
        for page in iterate_paginated_api(
            notion.data_sources.query,
            data_source_id=data_source_id,
            page_size=100,
            result_type="page",
        ):
            props = page.get("properties", {})
            model_prop = props.get("Model ID", {})
            rich_text = model_prop.get("rich_text", [])
            if rich_text:
                seen.add(rich_text[0].get("plain_text", ""))
        return [x for x in seen if x]
    except Exception as e:
        print(f"⚠️ Connection Warning: {e}")
        return []

def fetch_and_clean_data():
    print("📡 Fetching raw data from Hugging Face...")
    models = hf_api.list_models(filter="agent", sort="downloads", limit=50)
    raw_data = []
    for m in models:
        raw_data.append({
            "Name": m.modelId,
            "Downloads": getattr(m, 'downloads', 0) or 0,
            "Link": f"https://huggingface.co/{m.modelId}",
            "Tags": getattr(m, 'tags', [])
        })
    return pd.DataFrame(raw_data)

def sync_to_notion(df):
    try:
        data_source_id = resolve_data_source_id()
    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        print("➡️ Make sure the exact Notion database (or data source) is shared with your integration.")
        return

    existing_ids = get_existing_ids(data_source_id)
    new_entries = 0
    print(f"Syncing to Data Source: {data_source_id}...")
    
    for _, row in df.iterrows():
        if row["Name"] in existing_ids:
            continue 
            
        clean_name = row["Name"].split('/')[-1].replace('-', ' ').title()
        framework = "PyTorch" if "pytorch" in row["Tags"] else ("Transformers" if "transformers" in row["Tags"] else "Other")

        try:
            notion.pages.create(
                parent={"data_source_id": data_source_id},
                properties={
                    "Name": {"title": [{"text": {"content": clean_name}}]},
                    "Model ID": {"rich_text": [{"text": {"content": row["Name"]}}]},
                    "Framework": {"select": {"name": framework}},
                    "Downloads": {"number": row["Downloads"]},
                    "Source": {"url": row["Link"]},
                    "Status": {"select": {"name": "🔥 Trending" if row["Downloads"] > 500 else "🛠️ Research"}}
                }
            )
            new_entries += 1
        except Exception as e:
            print(f"❌ Entry Error: {e}")
            
    print(f"✅ Sync Complete! Added {new_entries} new records.")

if __name__ == "__main__":
    cleaned_df = fetch_and_clean_data()
    sync_to_notion(cleaned_df)