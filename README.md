# Battery Patent Analysis

Pipeline project for collecting, cleaning, analyzing, and reporting battery patent trends.

## Project Structure

```text
battery-patent-analysis/
├── data/
│   ├── raw/
│   │   └── raw_patents.csv
│   └── cleaned/
│       └── cleaned_patents.csv
├── scripts/
│   ├── 01_scraper.py
│   ├── 02_cleaner.py
│   └── 03_analysis.py
├── visualizations/
│   ├── fig1_yearly_trends.png
│   ├── fig2_top_firms.png
│   ├── fig3_tech_categories.png
│   └── fig4_country_heatmap.png
├── report/
│   └── analytical_report.pdf
├── requirements.txt
├── README.md
└── ai_declaration.md
```

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the pipeline scripts in order:

```bash
python scripts/01_scraper.py
python scripts/02_cleaner.py
python scripts/03_analysis.py
```

## Notes

- The current scripts are scaffolds/placeholders so the workflow can be expanded incrementally.
- The analysis script creates placeholder output files if they do not already exist.