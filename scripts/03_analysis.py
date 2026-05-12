"""Generate key analysis charts from the cleaned battery patent dataset."""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

INPUT_PATH = os.path.join("data", "cleaned", "final.csv") 
VIS_DIR = "visualizations"
REPORT_DIR = "report"

os.makedirs(VIS_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams['figure.figsize'] = (12, 7)
plt.rcParams['figure.dpi'] = 300 

def calc_cagr(start_val, end_val, periods):
    if start_val == 0 or periods == 0: return 0
    return ((end_val / start_val) ** (1 / periods) - 1) * 100

def main():
    if not os.path.exists(INPUT_PATH):
        print(f"[!] Error: Cleaned data not found at {INPUT_PATH}")
        return

    df = pd.read_csv(INPUT_PATH)
    df = df[df['Publication Year'] >= 2014] 
    df['Primary Assignee'] = df['Primary Assignee'].fillna("Unknown")
    df['Technology Category'] = df['Technology Category'].fillna("Other / General")

    print("[*] Generating Chart 1: Temporal Evolution...")
    plt.figure()
    yearly_counts = df['Publication Year'].value_counts().sort_index().reset_index()
    yearly_counts.columns = ['Year', 'Patent Count']
    sns.lineplot(data=yearly_counts, x='Year', y='Patent Count', marker='o', color='#2b83ba', linewidth=3)
    plt.fill_between(yearly_counts['Year'], yearly_counts['Patent Count'], alpha=0.15, color='#2b83ba')
    
    if len(yearly_counts) > 1:
        s_yr, e_yr = yearly_counts['Year'].min(), yearly_counts['Year'].max()
        s_cnt = yearly_counts[yearly_counts['Year'] == s_yr]['Patent Count'].values[0]
        e_cnt = yearly_counts[yearly_counts['Year'] == e_yr]['Patent Count'].values[0]
        cagr = calc_cagr(s_cnt, e_cnt, e_yr - s_yr)
        plt.annotate(f"CAGR ({s_yr}-{e_yr}): {cagr:.1f}%", xy=(0.05, 0.9), xycoords='axes fraction', 
                     fontsize=12, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray"))
    
    plt.title('Insight 1: Battery Patent Publication Momentum', fontweight='bold')
    plt.xlabel('Publication Year')
    plt.ylabel('Volume of Patents')
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "01_Temporal_Evolution.png"))
    plt.close()

    print("[*] Generating Chart 2: Firm Dominance...")
    plt.figure()
    corp_df = df[~df['Primary Assignee'].str.contains("Unknown|University|Institute", case=False, na=False)]
    top_firms = corp_df['Primary Assignee'].value_counts().head(10)
    sns.barplot(x=top_firms.values, y=top_firms.index, palette="mako")
    plt.title('Insight 2: Top 10 Corporate Entities Driving IP', fontweight='bold')
    plt.xlabel('Total Patents Assigned')
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "02_Firm_Dominance.png"))
    plt.close()

    print("[*] Generating Chart 3: Competitive Intelligence Heatmap...")
    plt.figure(figsize=(14, 8))
    top_5_firms = top_firms.head(5).index.tolist()
    heatmap_data = df[df['Primary Assignee'].isin(top_5_firms)]
    pivot_df = pd.crosstab(heatmap_data['Primary Assignee'], heatmap_data['Technology Category'])
    sns.heatmap(pivot_df, annot=True, cmap="YlGnBu", fmt="d", linewidths=.5)
    plt.title('Insight 3: R&D Portfolio Strategy of Top 5 Firms', fontweight='bold')
    plt.xlabel('Technology Category')
    plt.ylabel('Corporate Entity')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "03_Firm_Tech_Heatmap.png"))
    plt.close()

    print("[*] Generating Chart 4: Macro Technology Shifts...")
    plt.figure()
    tech_df = df[df['Technology Category'] != 'Other / General']
    tech_trends = tech_df.groupby(['Publication Year', 'Technology Category']).size().unstack(fill_value=0)
    tech_trends_pct = tech_trends.div(tech_trends.sum(axis=1), axis=0) * 100
    tech_trends_pct.plot(kind='area', stacked=True, colormap='tab20', alpha=0.8, figsize=(12, 7))
    plt.title('Insight 4: Evolution of Battery Technology Focus (Relative Share)', fontweight='bold')
    plt.xlabel('Publication Year')
    plt.ylabel('Percentage of Published Patents (%)')
    plt.legend(title='Technology Category', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "04_Technology_Shifts.png"))
    plt.close()

    

if __name__ == "__main__":
    main()