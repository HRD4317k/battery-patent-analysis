"""
Script: 01_scraper.py
Description: Scrapes battery-related patent data from Lens.org API
Author: Rishabh Dehariya
Date: May 2026

Covers: US, China (CN), Japan (JP), and European Patent Office (EP)
Topic: Battery technologies including lithium-ion, solid-state, EV batteries
"""

import requests
import pandas as pd
import json
import time
import os

# CONFIGURATION
API_TOKEN = "YOUR_LENS_API_TOKEN_HERE"   # <-- Replace this

BASE_URL = "https://api.lens.org/patent/search"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Search queries to cover different battery tech aspects
SEARCH_QUERIES = [
    "lithium-ion battery electric vehicle",
    "solid-state battery electrolyte",
    "battery energy storage system grid",
    "battery cathode anode electrode",
    "battery thermal management safety",
    "battery recycling second life",
    "battery charging fast charging",
]

# Countries / jurisdictions to cover
JURISDICTIONS = ["US", "CN", "JP", "EP"]

# Year range
DATE_FROM = "2013-01-01"
DATE_TO   = "2024-12-31"


def build_query_body(search_term, size=20, scroll_id=None):
    """Builds the POST request body for Lens.org API."""
    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": search_term,
                            "fields": ["title", "abstract"]
                        }
                    }
                ],
                "filter": [
                    {
                        "range": {
                            "date_published": {
                                "gte": DATE_FROM,
                                "lte": DATE_TO
                            }
                        }
                    },
                    {
                        "terms": {
                            "jurisdiction": JURISDICTIONS
                        }
                    }
                ]
            }
        },
        "size": size,
        "include": [
            "lens_id",
            "title",
            "date_published",
            "jurisdiction",
            "assignees",
            "inventors",
            "classifications",
            "abstract"
        ],
        "sort": [{"date_published": "desc"}]
    }
    if scroll_id:
        body["scroll_id"] = scroll_id
    else:
        body["scroll"] = "1m"

    return body


def fetch_patents(search_term, max_results=30):
    """Fetches patents from Lens.org for a given search term."""
    all_patents = []
    scroll_id = None
    fetched = 0

    print(f"\nFetching patents for: '{search_term}'")

    while fetched < max_results:
        batch_size = min(20, max_results - fetched)
        body = build_query_body(search_term, size=batch_size, scroll_id=scroll_id)

        try:
            response = requests.post(BASE_URL, headers=HEADERS, json=body)

            if response.status_code == 200:
                data = response.json()
                hits = data.get("data", [])

                if not hits:
                    print(f"No more results.")
                    break

                all_patents.extend(hits)
                fetched += len(hits)
                scroll_id = data.get("scroll_id")
                print(f"Fetched {fetched} patents so far...")

                # Respect rate limits — be polite to the API
                time.sleep(1.5)

                if len(hits) < batch_size:
                    break  # No more pages

            elif response.status_code == 429:
                print("  ⚠️  Rate limited. Waiting 30 seconds...")
                time.sleep(30)

            else:
                print(f"Error {response.status_code}: {response.text}")
                break

        except Exception as e:
            print(f"Exception: {e}")
            break

    return all_patents


def parse_patent(patent_raw):
    """
    Parses a single raw patent dict from Lens.org into a flat record.
    Returns a dictionary with all required fields.
    """
    # Title
    title_data = patent_raw.get("title", [])
    if isinstance(title_data, list) and title_data:
        title = title_data[0].get("text", "Unknown")
    else:
        title = str(title_data) if title_data else "Unknown"

    # Publication date and year
    date_published = patent_raw.get("date_published", "")
    year = date_published[:4] if date_published else "Unknown"

    # Jurisdiction (country)
    jurisdiction = patent_raw.get("jurisdiction", "Unknown")

    # Assignee (firm/organization)
    assignees = patent_raw.get("assignees", [])
    if assignees:
        # Take the first assignee's name
        assignee_name = assignees[0].get("name", "Unknown")
        assignee_country = assignees[0].get("country_code", jurisdiction)
    else:
        assignee_name = "Unknown"
        assignee_country = jurisdiction

    # Technology category (IPC classification)
    classifications = patent_raw.get("classifications", {})
    ipc_list = classifications.get("ipc", [])
    if ipc_list:
        # First IPC code — e.g., H01M (Primary Cells/Batteries)
        ipc_code = ipc_list[0].get("symbol", "Unknown")
        tech_category = map_ipc_to_category(ipc_code)
    else:
        ipc_code = "Unknown"
        tech_category = "General Battery Technology"

    # Application area (derived from IPC or title keywords)
    application_area = derive_application_area(title)

    # Abstract
    abstract_data = patent_raw.get("abstract", [])
    if isinstance(abstract_data, list) and abstract_data:
        abstract = abstract_data[0].get("text", "")[:500]  # First 500 chars
    else:
        abstract = ""

    return {
        "lens_id": patent_raw.get("lens_id", ""),
        "title": title,
        "date_published": date_published,
        "year": year,
        "jurisdiction": jurisdiction,
        "assignee_name": assignee_name,
        "assignee_country": assignee_country,
        "ipc_code": ipc_code,
        "technology_category": tech_category,
        "application_area": application_area,
        "abstract": abstract
    }


def map_ipc_to_category(ipc_code):
    """
    Maps IPC classification codes to human-readable battery technology categories.
    IPC codes relevant to batteries:
    H01M = Primary/Secondary Cells (batteries core)
    H01G = Capacitors/Supercapacitors
    B60L = Electric propulsion (EV)
    C01D/C01G = Inorganic chemistry (materials)
    H02J = Power supply circuits (charging/grid)
    """
    if not ipc_code or ipc_code == "Unknown":
        return "General Battery Technology"

    code = ipc_code[:4].upper()

    mapping = {
        "H01M": "Battery Cells & Electrochemistry",
        "H01G": "Capacitors & Energy Storage",
        "B60L": "Electric Vehicle Propulsion",
        "H02J": "Charging & Grid Integration",
        "C01D": "Battery Materials & Chemistry",
        "C01G": "Battery Materials & Chemistry",
        "H02B": "Power Distribution",
        "B60K": "Vehicle Drivetrain & Power",
        "H02M": "Power Conversion",
        "C22C": "Metal Alloys for Batteries",
    }

    for prefix, category in mapping.items():
        if code.startswith(prefix):
            return category

    return "General Battery Technology"


def derive_application_area(title):
    """
    Derives the application area from the patent title using keyword matching.
    """
    title_lower = title.lower()

    if any(k in title_lower for k in ["electric vehicle", "ev battery", "automotive", "car", "vehicle"]):
        return "Electric Vehicles"
    elif any(k in title_lower for k in ["grid", "energy storage", "power station", "microgrid", "utility"]):
        return "Grid Energy Storage"
    elif any(k in title_lower for k in ["solid state", "solid-state", "ceramic electrolyte"]):
        return "Solid-State Batteries"
    elif any(k in title_lower for k in ["recycle", "recycling", "second life", "reuse", "repurpose"]):
        return "Battery Recycling"
    elif any(k in title_lower for k in ["fast charg", "rapid charg", "charging station", "charger"]):
        return "Charging Infrastructure"
    elif any(k in title_lower for k in ["thermal", "safety", "fire", "cooling", "temperature"]):
        return "Battery Safety & Thermal"
    elif any(k in title_lower for k in ["cathode", "anode", "electrode", "electrolyte", "lithium"]):
        return "Electrochemistry & Materials"
    elif any(k in title_lower for k in ["portable", "consumer", "smartphone", "laptop", "wearable"]):
        return "Consumer Electronics"
    else:
        return "General Battery Technology"


def main():
    """Main function: scrapes all queries and saves raw + structured data."""

    all_parsed_patents = []
    all_raw_data = []
    seen_ids = set()  # To avoid duplicates

    for query in SEARCH_QUERIES:
        raw_patents = fetch_patents(query, max_results=30)

        for patent in raw_patents:
            lens_id = patent.get("lens_id", "")
            if lens_id in seen_ids:
                continue  # Skip duplicates
            seen_ids.add(lens_id)

            all_raw_data.append(patent)
            parsed = parse_patent(patent)
            all_parsed_patents.append(parsed)

        print(f"Total unique patents so far: {len(all_parsed_patents)}")
        time.sleep(2)  # Pause between queries

    print(f"\n Total unique patents collected: {len(all_parsed_patents)}")

    # raw data as JSON
    os.makedirs("data/raw", exist_ok=True)
    raw_path = "data/raw/raw_patents.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_raw_data, f, ensure_ascii=False, indent=2)
    print(f"Raw data saved to: {raw_path}")

    # raw data as CSV
    df_raw = pd.DataFrame(all_parsed_patents)  # Flat structure  {easier to read}
    df_raw.to_csv("data/raw/raw_patents.csv", index=False, encoding="utf-8")
    print(f"Raw CSV saved to: data/raw/raw_patents.csv")

    print(f"\nSample of collected data:")
    print(df_raw[["title", "year", "jurisdiction", "assignee_name", "technology_category"]].head(10))


if __name__ == "__main__":
    main()