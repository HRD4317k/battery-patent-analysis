# Battery Patent Analysis

End-to-end pipeline for collecting, cleaning, preprocessing, and analyzing battery patent data.

## What this project does

1. Pulls battery-related patents from Lens.org API.
2. Cleans and deduplicates records.
3. Enriches data with technology and application tagging.
4. Runs a final preprocessing pass for analysis-ready output.
5. Generates core visualizations for trend and firm-level insights.

## Project Structure

```text
battery-patent-analysis/
├── data/
│   ├── raw/
│   │   ├── raw_patents.csv
│   │   └── raw_patents.json
│   └── cleaned/
│       ├── cleaned_patents.csv
│       └── final.csv
├── scripts/
│   ├── 01_scraper.py
│   ├── 02_cleaner.py
│   ├── 02_5_preprocessing.py
│   └── 03_analysis.py
├── visualizations/
│   ├── 01_Temporal_Evolution.png
│   ├── 02_Firm_Dominance.png
│   ├── 03_Firm_Tech_Heatmap.png
│   └── 04_Technology_Shifts.png
├── report/
├── requirements.txt
├── README.md
└── ai_declaration.md
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set Lens API token as environment variable:

Windows PowerShell:

```powershell
$env:LENS_API_TOKEN="your_lens_token_here"
```

## Run Pipeline

Run scripts in this exact order:

```bash
python scripts/01_scraper.py
python scripts/02_cleaner.py
python scripts/02_5_preprocessing.py
python scripts/03_analysis.py
```

## Outputs

- Raw scraped data: `data/raw/raw_patents.csv`
- Cleaned + tagged data: `data/cleaned/cleaned_patents.csv`
- Final analysis-ready data: `data/cleaned/final.csv`
- Charts are saved in `visualizations/`

## Script Summary

- `01_scraper.py`
	- Connects to Lens.org API and fetches patents for battery-focused queries.
	- Filters by jurisdiction (US, CN, JP, EP) and date range (2014-01-01 to 2024-12-31).

- `02_cleaner.py`
	- Removes duplicates and standardizes key columns.
	- Uses NLTK-based normalization and ontology scoring for:
		- Technology Category
		- Application Area
	- Extracts and normalizes primary assignee names.

- `02_5_preprocessing.py`
	- Applies final keyword filtering and cleanup.
	- Maps country codes to names.
	- Cleans assignee text and recomputes high-level categories.
	- Exports `final.csv`.

- `03_analysis.py`
	- Builds 4 charts for publication trends, top firms, firm-tech heatmap, and tech-share shifts.

## Notes

- Make sure `LENS_API_TOKEN` is set before running scraper.
- NLTK resources are downloaded automatically on first run of cleaner if missing.