"""Fetch battery-related patents from Lens.org and save them as CSV."""

import requests
import pandas as pd
import time
import os

# Put your Lens API token in the LENS_API_TOKEN environment variable.
API_TOKEN = os.getenv("LENS_API_TOKEN")

BASE_URL = "https://api.lens.org/patent/search"
HEADERS  = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type":  "application/json"
}

JURISDICTIONS = ["US", "CN", "JP", "EP"]
DATE_FROM     = "2014-01-01"
DATE_TO       = "2024-12-31"

# Simple keyword queries we cycle through.
QUERIES = [
    "lithium ion battery electric vehicle",
    "solid state battery electrolyte",
    "battery energy storage system",
    "cathode anode electrode lithium battery",
    "battery thermal management safety",
    "lithium battery recycling second life",
    "fast charging lithium battery",
    "sodium ion battery electrode",
]


def test_connection():
    """
    Fires a minimal query to verify the token and API schema are working.
    """
    print("Testing API connection...")
    body = {
        "query": {
            "query_string": {
                "query": "battery"
            }
        },
        "size": 1
    }
    try:
        r = requests.post(BASE_URL, headers=HEADERS, json=body, timeout=20)
        if r.status_code == 200:
            data  = r.json()
            total = data.get("total", 0)
            print(f"  [+] Connection OK. Total 'battery' patents in Lens.org: {total:,}")
            sample = data.get("data", [])
            if sample:
                biblio = sample[0].get("biblio", {})
                titles = biblio.get("invention_title", [])
                t = titles[0].get("text", "") if titles else "N/A"
                print(f"  [+] Sample title: {t[:80]}")
            return True
        elif r.status_code == 401:
            print(f"  [-] FAIL 401 - Invalid or expired token.")
            return False
        else:
            print(f"  [-] FAIL {r.status_code}: {r.text[:300]}")
            return False
    except Exception as e:
        print(f"  [-] Connection error: {e}")
        return False


def build_body(term, size=20, scroll_id=None):
    """
    Builds the JSON payload for the Lens API.
    Keeps the payload simple so it stays compatible with the API schema.
    """
    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": term
                        }
                    }
                ],
                "filter": [
                    {
                        "terms": {
                            "jurisdiction": JURISDICTIONS
                        }
                    },
                    {
                        "range": {
                            "date_published": {
                                "gte": DATE_FROM,
                                "lte": DATE_TO
                            }
                        }
                    }
                ]
            }
        },
        "size": size,
    }
    if scroll_id:
        body["scroll_id"] = scroll_id
    else:
        body["scroll"] = "1m"
    return body


def fetch(term, max_results=100):
    results   = []
    scroll_id = None
    fetched   = 0
    print(f"\n[*] Searching: '{term}'")

    while fetched < max_results:
        batch = min(20, max_results - fetched)
        body  = build_body(term, size=batch, scroll_id=scroll_id)

        try:
            r = requests.post(BASE_URL, headers=HEADERS, json=body, timeout=30)
        except requests.exceptions.Timeout:
            print("     Timeout - retrying in 15s...")
            time.sleep(15)
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"     Connection error: {e}")
            break

        if r.status_code == 200:
            data  = r.json()
            hits  = data.get("data", [])
            total = data.get("total", 0)

            if not hits:
                print(f"     No results returned (total available: {total})")
                break

            results.extend(hits)
            fetched   += len(hits)
            scroll_id  = data.get("scroll_id")
            print(f"     Fetched {fetched} (total in Lens.org: {total:,})")
            time.sleep(1.2)  # Small pause so we do not hammer the API.

            if len(hits) < batch:
                break

        elif r.status_code == 429:
            print("     Rate-limited - waiting 30s...")
            time.sleep(30)

        elif r.status_code == 401:
            print("     401 Unauthorized - token is wrong or expired. Stopping.")
            return []

        else:
            print(f"     HTTP {r.status_code}: {r.text[:250]}")
            break

    return results


def _first_title(title_list):
    if not isinstance(title_list, list) or not title_list:
        return ""
    for t in title_list:
        if isinstance(t, dict) and t.get("lang", "").lower() in ("en", ""):
            return t.get("text", "").strip()
    first = title_list[0]
    return first.get("text", "").strip() if isinstance(first, dict) else ""


def _first_abstract(abs_list):
    if not isinstance(abs_list, list) or not abs_list:
        return ""
    for a in abs_list:
        if isinstance(a, dict) and a.get("lang", "").lower() in ("en", ""):
            return a.get("text", "").strip()
    first = abs_list[0]
    return first.get("text", "").strip() if isinstance(first, dict) else ""


def _join_names(people_list):
    names = []
    for p in (people_list or []):
        if not isinstance(p, dict):
            continue
        extracted = p.get("extracted_name", {})
        name = extracted.get("value", "") if isinstance(extracted, dict) else ""
        if not name:
            name = p.get("name", "")
        if name:
            names.append(name.strip())
    return ";;".join(names) if names else ""


def parse_one(raw):
    # Pull fields carefully because some records are sparse.
    biblio   = raw.get("biblio", {}) or {}
    parties  = biblio.get("parties", {}) or {}
    
    lens_id      = raw.get("lens_id", "")
    jurisdiction = raw.get("jurisdiction", "")
    date_pub     = raw.get("date_published", "")
    pub_year     = int(date_pub[:4]) if date_pub and len(date_pub) >= 4 else None

    applicants = _join_names(parties.get("applicants", []))
    inventors  = _join_names(parties.get("inventors",  []))

    return {
        "Lens ID":           lens_id,
        "Jurisdiction":      jurisdiction,
        "Publication Date":  date_pub,
        "Publication Year":  pub_year,
        "Title":             _first_title(biblio.get("invention_title", [])),
        "Abstract":          _first_abstract(raw.get("abstract", [])),
        "Applicants":        applicants,
        "Inventors":         inventors,
        "URL":               f"https://lens.org/{lens_id}"
    }


def main():
    os.makedirs(os.path.join("data", "raw"), exist_ok=True)
    os.makedirs(os.path.join("data", "cleaned"), exist_ok=True)

    print("=" * 65)
    print("  BATTERY PATENT SCRAPER  -  Lens.org API")
    print(f"  Jurisdictions : {JURISDICTIONS}")
    print(f"  Date range    : {DATE_FROM}  to  {DATE_TO}")
    print("=" * 65)

    if not test_connection():
        print("\n[!] Stopped: API connection failed.")
        return

    print()
    all_records = []
    seen_ids    = set()

    for term in QUERIES:
        raw_list = fetch(term, max_results=100) 
        new = 0
        for raw in raw_list:
            lid = raw.get("lens_id", "")
            if lid and lid in seen_ids:
                continue
            seen_ids.add(lid)
            all_records.append(parse_one(raw))
            new += 1
        print(f"  [+] {new} new  |  Total unique so far: {len(all_records)}")
        time.sleep(2)

    print(f"\n{'='*65}")
    print(f"  TOTAL UNIQUE PATENTS COLLECTED: {len(all_records)}")
    print(f"{'='*65}\n")

    if not all_records:
        print("Zero patents collected. Check query strings or date parameters.")
        return

    df = pd.DataFrame(all_records)
    df.insert(0, "#", range(1, len(df) + 1))
    
    csv_path = os.path.join("data", "raw", "raw_patents.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8")

    print(f"Raw CSV saved -> {csv_path} ({len(df)} rows)")
    print("\nPreview:")
    print(df[["#", "Jurisdiction", "Publication Year", "Title"]].head(10).to_string(index=False))

if __name__ == "__main__":
    main()