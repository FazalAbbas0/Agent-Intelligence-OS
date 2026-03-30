import os
import time
import logging
import re
import pandas as pd
from huggingface_hub import HfApi
from notion_client import Client
from notion_client.helpers import extract_notion_id, iterate_paginated_api
from notion_client.errors import APIResponseError
from dotenv import load_dotenv

try:
    from google import genai
except ImportError:
    genai = None

load_dotenv()

# Setup logging
os.makedirs("metadata", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("metadata/factory_health.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Clean ID and Initialize
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
notion = Client(auth=NOTION_TOKEN)
hf_api = HfApi()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
MODEL_LIMIT = int(os.getenv("MODEL_LIMIT", "4"))
ARCHITECT_MODEL = os.getenv("GEMINI_ARCHITECT_MODEL", "gemini-2.0-flash").strip()
client = None

if genai and GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
elif not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set. Architect suite generation will be skipped.")
else:
    logger.warning("google-genai is not installed. Architect suite generation will be skipped.")

# Industry mapping
INDUSTRY_MAP = {
    "vision": "Computer Vision (CV)",
    "image": "Computer Vision (CV)",
    "object-detection": "Computer Vision (CV)",
    "image-classification": "Computer Vision (CV)",
    "data": "Data Science",
    "tabular": "Data Science",
    "timeseries": "Data Science",
    "regression": "Data Science",
    "clustering": "Data Science",
    "security": "Cybersecurity",
    "cyber": "Cybersecurity",
    "intrusion": "Cybersecurity",
    "iot": "IoT & Edge AI",
    "edge": "IoT & Edge AI",
    "robotics": "IoT & Edge AI",
    "embedded": "IoT & Edge AI",
    "legal": "Legal & Compliance",
    "compliance": "Legal & Compliance",
    "contract": "Legal & Compliance",
    "finance": "Finance & Fintech",
    "fintech": "Finance & Fintech",
    "banking": "Finance & Fintech",
    "trading": "Finance & Fintech",
    "support": "Customer Support",
    "chatbot": "Customer Support",
    "qa": "Customer Support",
    "health": "Healthcare",
    "medical": "Healthcare",
    "clinical": "Healthcare",
    "diagnosis": "Healthcare",
    "ecommerce": "E-commerce",
    "recommendation": "E-commerce",
    "product": "E-commerce",
    "education": "Education",
    "learning": "Education",
    "tutor": "Education",
    "course": "Education",
    "creative": "Creative Arts",
    "art": "Creative Arts",
    "music": "Creative Arts",
    "generation": "Creative Arts",
    "codegen": "Automated Python Generation",
    "code-generation": "Automated Python Generation",
    "programming": "Automated Python Generation",
}


def _normalize_notion_id(value):
    parsed = extract_notion_id(value or "")
    if not parsed:
        raise ValueError("Invalid Notion ID/URL. Please provide a valid UUID or Notion URL.")
    return parsed


def get_industry_and_usecase(tags):
    """Return Industry label matching Notion Select options."""
    if not tags:
        return "Others"
    
    tags_lower = [tag.lower() for tag in tags]
    full_text = " ".join(tags_lower)
    
    for keyword, industry in INDUSTRY_MAP.items():
        if keyword in full_text:
            logger.info(f"Industry matched: {keyword} -> {industry}")
            return industry
    
    logger.info("No industry keyword match; using 'Others'")
    return "Others"


def extract_quantization(tags):
    """Scan tags for quantization formats: GGUF, AWQ, EXL2."""
    if not tags:
        return None
    
    quant_formats = ["GGUF", "AWQ", "EXL2"]
    tags_upper = [tag.upper() for tag in tags]
    
    for fmt in quant_formats:
        if any(fmt in tag for tag in tags_upper):
            logger.info(f"Quantization detected: {fmt}")
            return fmt
    
    return None


def extract_context_window(tags):
    """Extract numerical context window values (e.g., 32k, 128k, 4096)."""
    if not tags:
        return None
    
    full_text = " ".join(tags).lower()
    
    # Match patterns like 32k, 128k, 4096
    match = re.search(r'(\d+)k?(?=\s|$|[,\]])', full_text)
    if match:
        value = int(match.group(1))
        if value > 100:  # Likely a context window
            logger.info(f"Context window detected: {value}")
            return value
    
    return None


def calculate_review_score(likes, downloads):
    """
    Calculate Review Score (1.0 to 5.0).
    Formula: (Likes / (Downloads + 1)) * 1000, capped at 5.0
    """
    likes = max(0, likes if likes else 0)
    downloads = max(0, downloads if downloads else 0)
    
    score = (likes / (downloads + 1)) * 1000
    capped_score = min(score, 5.0)
    logger.info(f"Review score calculated: {capped_score} (likes={likes}, downloads={downloads})")
    return capped_score


def _build_rich_text_blocks(text, max_chars=2000):
    """Split long text into Notion rich_text blocks under per-block limits."""
    if not text:
        return []

    blocks = []
    # Notion rich_text content limit is 2000 chars per text block.
    strict_limit = min(max_chars, 2000)
    start = 0
    while start < len(text):
        chunk = text[start:start + strict_limit]
        start += strict_limit
        blocks.append({"text": {"content": chunk}})
    return blocks


def _extract_section(full_text, start_marker, end_markers):
    start_idx = full_text.find(start_marker)
    if start_idx < 0:
        return ""

    end_idx = len(full_text)
    for marker in end_markers:
        marker_idx = full_text.find(marker, start_idx + len(start_marker))
        if marker_idx >= 0:
            end_idx = min(end_idx, marker_idx)

    return full_text[start_idx:end_idx].strip()


def get_architect_suite(model_id, industry):
    """Generate monetization-ready implementation suite with Gemini 2.0 Flash."""
    if not client:
        return None

    prompt = f"""
You are an Elite Agentic AI Architect & Business Consultant.

Mission: Build a No-Coder Franchise playbook for global freelancers and 15-year-old beginners.

Model: {model_id}
Industry: {industry}

Output MUST include these exact section headers:

[DOCKER & NO-CODE SETUP]
- Assume Docker Desktop is already installed.
- Explain each step so simply that a matric student can follow it.
- Include a complete Dockerfile.
- Include a complete docker-compose.yml.
- Include exactly this speed line: Manual Work: 4 Hours | This Suite: 2 Minutes.

[THE $150 FREELANCE GIG]
- One ready-made Upwork/Fiverr title.
- One ready-to-paste gig description that is beginner-friendly and client-focused.

[THE CLIENT OBJECTION KILLER]
- Exactly 3 FAQs with concise answers to close business clients.

[GUMROAD COPY]
- Product title format: [Business-in-a-Box] {model_id}
- Position this as a $10 offer.
- Add compelling, conversion-focused copy for global buyers.

Formatting rules:
- Use markdown.
- Keep code blocks valid and copy-paste ready.
- Be concrete, practical, and no-jargon.
""".strip()

    try:
        result = client.models.generate_content(
            model=ARCHITECT_MODEL,
            contents=prompt,
        )

        full_text = (result.text or "").strip()
        if not full_text:
            return None

        docker_payload = "\n\n".join([
            _extract_section(
                full_text,
                "[DOCKER & NO-CODE SETUP]",
                ["[THE $150 FREELANCE GIG]", "[THE CLIENT OBJECTION KILLER]", "[GUMROAD COPY]"],
            ),
        ]).strip()

        gumroad_copy = "\n\n".join([
            _extract_section(
                full_text,
                "[THE $150 FREELANCE GIG]",
                ["[THE CLIENT OBJECTION KILLER]", "[GUMROAD COPY]"],
            ),
            _extract_section(
                full_text,
                "[THE CLIENT OBJECTION KILLER]",
                ["[GUMROAD COPY]", "[THE $150 FREELANCE GIG]"],
            ),
            _extract_section(
                full_text,
                "[GUMROAD COPY]",
                ["[THE CLIENT OBJECTION KILLER]", "[THE $150 FREELANCE GIG]"],
            ),
        ]).strip()

        # Fallback in case section parsing fails.
        if not docker_payload:
            docker_payload = full_text
        if not gumroad_copy:
            gumroad_copy = full_text

        return {
            "full_text": full_text,
            "docker_payload": docker_payload,
            "gumroad_copy": gumroad_copy,
        }
    except Exception as e:
        logger.error(f"Gemini architect generation failed for {model_id}: {e}")
        return None



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

def get_existing_pages(data_source_id):
    """Fetch existing pages keyed by Model ID from a Notion data source."""
    try:
        pages_by_model_id = {}
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
                model_id = rich_text[0].get("plain_text", "")
                if model_id:
                    pages_by_model_id[model_id] = page
        return pages_by_model_id
    except Exception as e:
        print(f"⚠️ Connection Warning: {e}")
        return {}


def _is_rich_text_empty(prop):
    """Return True when a Notion rich_text property has no visible content."""
    rich_text_items = (prop or {}).get("rich_text", [])
    for item in rich_text_items:
        plain_text = (item.get("plain_text") or "").strip()
        if plain_text and plain_text.lower() not in {"-", ".", "n/a"}:
            return False
    return True


def get_data_source_property_types(data_source_id):
    """Return a map of property name -> Notion property type for the target data source."""
    try:
        data_source = notion.data_sources.retrieve(data_source_id=data_source_id)
        properties = data_source.get("properties", {})
        return {
            name: details.get("type")
            for name, details in properties.items()
            if isinstance(details, dict)
        }
    except Exception as e:
        logger.warning(f"Could not retrieve data source properties: {e}")
        return {}


def _log_notion_api_error(action, model_name, error):
    """Log detailed Notion API errors without stopping the sync loop."""
    status = getattr(error, "status", "unknown")
    code = getattr(error, "code", "unknown")
    message = getattr(error, "message", str(error))
    logger.error(
        f"Notion API error during {action} for {model_name}: status={status}, code={code}, message={message}"
    )
    print(f"[ERROR] Notion {action} failed for {model_name}: status={status}, code={code}")


def startup_env_check():
    """Print startup warnings for missing optional but recommended environment keys."""
    if not HF_TOKEN:
        logger.warning("HF_TOKEN is missing in .env. Public Hugging Face access will be used.")
        print("[WARNING] HF_TOKEN missing in .env; using public Hugging Face access.")
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is missing in .env. Architect enrichment will be skipped.")
        print("[WARNING] GEMINI_API_KEY missing in .env; Architect enrichment disabled.")

def fetch_and_clean_data():
    """Fetch and clean model data from Hugging Face with metadata extraction."""
    print("[FETCH] Fetching raw data from Hugging Face...")
    logger.info("Initiating Hugging Face data fetch...")
    
    try:
        models = hf_api.list_models(filter="agent", sort="downloads", limit=50)
    except Exception as e:
        logger.error(f"HF API Error: {e}. Check HF service status.")
        print(f"[ERROR] HF API Error: {e}")
        return pd.DataFrame()
    
    raw_data = []
    for m in models:
        try:
            tags = getattr(m, 'tags', []) or []
            downloads = getattr(m, 'downloads', 0) or 0
            likes = getattr(m, 'likes', 0) or 0
            
            # Extract metadata
            industry = get_industry_and_usecase(tags)
            quantization = extract_quantization(tags)
            context_window = extract_context_window(tags)
            review_score = calculate_review_score(likes, downloads)
            
            raw_data.append({
                "Name": m.modelId,
                "Downloads": downloads,
                "Likes": likes,
                "Link": f"https://huggingface.co/{m.modelId}",
                "Tags": tags,
                "Industry": industry,
                "Quantization": quantization,
                "Context Window": context_window,
                "Review Score": review_score,
            })
            logger.info(f"Processed model: {m.modelId}")
        except Exception as e:
            logger.warning(f"Error processing model {getattr(m, 'modelId', 'unknown')}: {e}")
            continue
    
    logger.info(f"Successfully fetched {len(raw_data)} models")
    df = pd.DataFrame(raw_data)
    if df.empty:
        return df

    architect_pool = (
        df[df["Review Score"] >= 0.0]
        .sort_values(by="Downloads", ascending=False)
        .head(MODEL_LIMIT)
    )
    architect_ids = set(architect_pool["Name"].tolist())
    df["Architect Candidate"] = df["Name"].isin(architect_ids)
    logger.info(f"Architect candidates selected: {len(architect_ids)}")
    return df

def get_vram_requirement(downloads, tags):
    """Determine VRAM requirement based on downloads and tags."""
    tags_lower = " ".join(tags).lower() if tags else ""
    
    if any(x in tags_lower for x in ["7b", "small", "lite"]):
        return "4GB"
    elif any(x in tags_lower for x in ["13b", "medium"]):
        return "8GB"
    elif any(x in tags_lower for x in ["34b", "40b", "large"]):
        return "16GB"
    elif any(x in tags_lower for x in ["70b", "xl", "extra"]):
        return "32GB"
    else:
        return "8GB"  # Default


def get_minimum_ram(downloads, tags):
    """Determine Minimum RAM requirement."""
    tags_lower = " ".join(tags).lower() if tags else ""
    
    if any(x in tags_lower for x in ["7b", "small", "lite"]):
        return "8GB"
    elif any(x in tags_lower for x in ["13b", "medium"]):
        return "16GB"
    elif any(x in tags_lower for x in ["34b", "40b", "large"]):
        return "32GB"
    elif any(x in tags_lower for x in ["70b", "xl", "extra"]):
        return "64GB"
    else:
        return "16GB"  # Default


def sync_to_notion(df):
    """Sync cleaned models to Notion with rate limiting and health logging."""
    try:
        data_source_id = resolve_data_source_id()
        logger.info(f"Resolved data source: {data_source_id}")
    except Exception as e:
        logger.error(f"Configuration Error: {e}")
        print(f"[ERROR] Configuration Error: {e}")
        print("[INFO] Make sure the exact Notion database (or data source) is shared with your integration.")
        return

    existing_pages = get_existing_pages(data_source_id)
    existing_ids = set(existing_pages.keys())
    property_types = get_data_source_property_types(data_source_id)
    new_entries = 0
    updated_entries = 0
    logger.info(f"Starting sync to Data Source: {data_source_id}...")
    print(f"[SYNC] Syncing to Data Source: {data_source_id}...")
    
    for idx, row in df.iterrows():
        try:
            model_exists = row["Name"] in existing_ids
            should_architect = bool(row.get("Architect Candidate", False))
            force_enrichment = False
            existing_page = {}

            if model_exists:
                existing_page = existing_pages.get(row["Name"], {})
                existing_props = existing_page.get("properties", {})
                docker_field_type = property_types.get("Docker Payload")
                gumroad_field_type = property_types.get("Gumroad Copy")

                docker_missing = (
                    _is_rich_text_empty(existing_props.get("Docker Payload", {}))
                )
                gumroad_missing = (
                    _is_rich_text_empty(existing_props.get("Gumroad Copy", {}))
                )
                force_enrichment = docker_missing or gumroad_missing

            run_architect_pass = should_architect or force_enrichment

            if model_exists and not run_architect_pass:
                skipped_name = row["Name"].split('/')[-1].replace('-', ' ').title()
                logger.info(f"[SKIPPED] Model already exists with no architect pass: {row['Name']}")
                print(f"[SKIPPED] {skipped_name}")
                continue

            clean_name = row["Name"].split('/')[-1].replace('-', ' ').title()
            model_name = row["Name"].split('/')[-1]
            run_command = f"ollama run {model_name}"
            
            vram_req = get_vram_requirement(row["Downloads"], row["Tags"])
            min_ram = get_minimum_ram(row["Downloads"], row["Tags"])
            status = "Trending" if row["Downloads"] > 5000 else "Research"
            
            # Safe context window handling
            context_window = row.get("Context Window")
            if pd.isna(context_window) or context_window is None:
                context_window = 4096
            context_window = int(context_window)
            
            review_score = row.get("Review Score", 1.0)
            if pd.isna(review_score):
                review_score = 1.0
            review_score = float(review_score)

            architect_suite = None
            industry_label = row.get("Industry", "Others")
            if run_architect_pass:
                logger.info(f"[ELITE-ARCHITECT] Processing {row['Name']}")
                architect_suite = get_architect_suite(row["Name"], industry_label)
            else:
                logger.info(f"[SYNC-ONLY] Syncing {row['Name']} without architect suite")

            if model_exists and run_architect_pass:
                existing_props = existing_page.get("properties", {})
                update_payload = {}

                if architect_suite:
                    docker_field_type = property_types.get("Docker Payload")
                    gumroad_field_type = property_types.get("Gumroad Copy")

                    if docker_field_type == "rich_text":
                        docker_prop = existing_props.get("Docker Payload", {})
                        if _is_rich_text_empty(docker_prop):
                            update_payload["Docker Payload"] = {
                                "rich_text": _build_rich_text_blocks(architect_suite["docker_payload"])
                            }

                    if gumroad_field_type == "rich_text":
                        gumroad_prop = existing_props.get("Gumroad Copy", {})
                        if _is_rich_text_empty(gumroad_prop):
                            update_payload["Gumroad Copy"] = {
                                "rich_text": _build_rich_text_blocks(architect_suite["gumroad_copy"])
                            }

                if update_payload:
                    try:
                        notion.pages.update(
                            page_id=existing_page["id"],
                            properties=update_payload,
                        )
                        updated_entries += 1
                        logger.info(f"[ENRICHING EXISTING] Updated architect payload for existing model: {row['Name']}")
                        print(f"[ENRICHING EXISTING] {clean_name}")
                        time.sleep(1)
                    except APIResponseError as api_error:
                        _log_notion_api_error("update", row["Name"], api_error)
                        continue
                    except Exception as update_error:
                        logger.error(f"Unexpected update error for {row['Name']}: {update_error}")
                        print(f"[ERROR] Unexpected update error for {row['Name']}")
                        continue
                else:
                    logger.info(f"[SKIPPED] Existing model already enriched: {row['Name']}")
                    print(f"[SKIPPED] {clean_name}")
                continue
            
            payload = {
                "Name": {"title": [{"text": {"content": clean_name}}]},
                "Model ID": {"rich_text": [{"text": {"content": row["Name"]}}]},
                "VRAM Required": {"select": {"name": vram_req}},
                "Minimum RAM": {"select": {"name": min_ram}},
                "Context Window": {"number": context_window},
                "Run Command": {"rich_text": [{"text": {"content": run_command}}]},
                "Review Score": {"number": review_score},
                "Status": {"select": {"name": status}},
                "Downloads": {"number": int(row["Downloads"])},
                "Source": {"url": row["Link"]},
            }

            industry_type = property_types.get("Industry")
            if industry_type == "multi_select":
                payload["Industry"] = {"multi_select": [{"name": industry_label}]}
            elif industry_type == "select":
                payload["Industry"] = {"select": {"name": industry_label}}
            else:
                logger.warning("Industry property missing or unsupported type; skipping Industry field.")
            
            # Add quantization if detected
            if "Quantization" in property_types and row.get("Quantization"):
                quant_type = property_types.get("Quantization")
                quant_value = row["Quantization"]
                if quant_type == "rich_text":
                    payload["Quantization"] = {"rich_text": [{"text": {"content": quant_value}}]}
                elif quant_type == "select":
                    payload["Quantization"] = {"select": {"name": quant_value}}
                elif quant_type == "multi_select":
                    payload["Quantization"] = {"multi_select": [{"name": quant_value}]}
                else:
                    logger.warning("Quantization property type unsupported; skipping Quantization field.")

            implementation_field_type = property_types.get("Implementation Link")
            if implementation_field_type == "url":
                payload["Implementation Link"] = {"url": None}
            elif implementation_field_type == "rich_text":
                payload["Implementation Link"] = {"rich_text": []}

            if architect_suite:
                docker_field_type = property_types.get("Docker Payload")
                gumroad_field_type = property_types.get("Gumroad Copy")

                if docker_field_type == "rich_text":
                    payload["Docker Payload"] = {
                        "rich_text": _build_rich_text_blocks(architect_suite["docker_payload"])
                    }
                if gumroad_field_type == "rich_text":
                    payload["Gumroad Copy"] = {
                        "rich_text": _build_rich_text_blocks(architect_suite["gumroad_copy"])
                    }
            
            try:
                notion.pages.create(
                    parent={"data_source_id": data_source_id},
                    properties=payload
                )
            except APIResponseError as api_error:
                _log_notion_api_error("create", row["Name"], api_error)
                continue
            except Exception as create_error:
                logger.error(f"Unexpected create error for {row['Name']}: {create_error}")
                print(f"[ERROR] Unexpected create error for {row['Name']}")
                continue
            
            new_entries += 1
            logger.info(f"[CREATED NEW] Successfully created page for: {row['Name']}")
            print(f"[CREATED NEW] {clean_name}")
            
            # Rate limiting to avoid 429 errors.
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Entry Error for {row['Name']}: {e}")
            print(f"[ERROR] Entry Error: {e}")
            continue

    logger.info(f"[COMPLETE] Sync Complete! Added {new_entries} new records. Updated {updated_entries} existing records.")
    print(f"[COMPLETE] Sync Complete! Added {new_entries} new records. Updated {updated_entries} existing records.")



if __name__ == "__main__":
    logger.info("[START] Intelligence Scout Phase 1.1...")
    print("[START] Intelligence Scout Phase 1.1...")
    startup_env_check()
    
    try:
        cleaned_df = fetch_and_clean_data()
        if not cleaned_df.empty:
            sync_to_notion(cleaned_df)
            logger.info("[SUCCESS] Script execution completed!")
        else:
            logger.warning("[WARNING] No data fetched from Hugging Face")
            print("[WARNING] No data fetched from Hugging Face")
    except Exception as e:
        logger.error(f"[FATAL] Error: {e}", exc_info=True)
        print(f"[FATAL] Error: {e}")
