"""Final preprocessing pass to build the analysis-ready patent dataset."""

import pandas as pd
import numpy as np
import re

INPUT_FILE = "data/cleaned/cleaned_patents.csv"
OUTPUT_FILE = "data/cleaned/final.csv"

print("=" * 60)
print("BATTERY PATENT PREPROCESSING STARTED")
print("=" * 60)

df = pd.read_csv(INPUT_FILE)

print(f"\nOriginal Dataset Shape: {df.shape}")

df.columns = [col.strip() for col in df.columns]

print("\nFiltering only battery-related patents...")

battery_keywords = [
    "battery",
    "lithium",
    "li-ion",
    "electrolyte",
    "anode",
    "cathode",
    "charging",
    "battery pack",
    "cell",
    "rechargeable",
    "bms",
    "thermal management",
    "fast charging",
    "solid state",
    "separator"
]

pattern = "|".join(battery_keywords)

df["combined_text"] = (
    df["Title"].fillna("").astype(str)
    + " "
    + df["Abstract"].fillna("").astype(str)
)

before_filter = len(df)

df = df[
    df["combined_text"]
    .str.lower()
    .str.contains(pattern, na=False)
]

after_filter = len(df)

print(f"Removed Non-Battery Patents: {before_filter - after_filter}")
print(f"Remaining Battery Patents: {after_filter}")

print("\nRemoving duplicates...")

before_dup = len(df)

if "Lens ID" in df.columns:
    df.drop_duplicates(subset=["Lens ID"], inplace=True)
else:
    df.drop_duplicates(inplace=True)

after_dup = len(df)

print(f"Duplicates Removed: {before_dup - after_dup}")

print("\nCleaning text columns...")

text_columns = [
    "Title",
    "Abstract",
    "Assignee (Applicant)",
    "Primary Assignee"
]

for col in text_columns:

    if col in df.columns:

        df[col] = (
            df[col]
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

print("\nMapping country codes...")

country_mapping = {
    "US": "United States",
    "JP": "Japan",
    "CN": "China",
    "EP": "European Patent Office"
}

df["Country"] = (
    df["Country"]
    .astype(str)
    .str.strip()
    .replace(country_mapping)
)

print("\nCleaning publication year...")

df["Publication Year"] = pd.to_numeric(
    df["Publication Year"],
    errors="coerce"
)

df = df[
    (df["Publication Year"] >= 2000) &
    (df["Publication Year"] <= 2025)
]

df["Publication Year"] = (
    df["Publication Year"]
    .astype(int)
)

print("\nCleaning assignee names...")

def clean_assignee(name):

    if pd.isna(name):
        return "Unknown"

    name = str(name).upper().strip()

    remove_words = [
        "LTD",
        "LIMITED",
        "INC",
        "CORP",
        "CORPORATION",
        "LLC",
        "CO",
        "COMPANY",
        "GMBH",
        "PLC"
    ]

    for word in remove_words:
        name = re.sub(rf"\b{word}\b", "", name)

    name = re.sub(r"\s+", " ", name)

    return name.strip()

if "Primary Assignee" not in df.columns:

    df["Primary Assignee"] = (
        df["Assignee (Applicant)"]
    )

df["Primary Assignee"] = (
    df["Primary Assignee"]
    .fillna("Unknown")
    .apply(clean_assignee)
)

print("\nCreating technology categories...")

def classify_technology(text):

    text = text.lower()

    if any(word in text for word in [
        "anode",
        "cathode",
        "electrolyte",
        "separator",
        "solid state"
    ]):
        return "Battery Chemistry"

    elif any(word in text for word in [
        "charging",
        "fast charging",
        "wireless charging",
        "charger"
    ]):
        return "Charging Technology"

    elif any(word in text for word in [
        "thermal",
        "cooling",
        "heat",
        "fire",
        "safety"
    ]):
        return "Thermal & Safety"

    elif any(word in text for word in [
        "battery pack",
        "module",
        "housing"
    ]):
        return "Battery Pack & Structure"

    elif any(word in text for word in [
        "manufacturing",
        "assembly",
        "production"
    ]):
        return "Manufacturing"

    elif any(word in text for word in [
        "recycling",
        "reuse",
        "second life"
    ]):
        return "Battery Recycling"

    else:
        return "Others"

df["Technology Category"] = (
    df["combined_text"]
    .apply(classify_technology)
)

print("\nCreating application areas...")

def classify_application(text):

    text = text.lower()

    if any(word in text for word in [
        "electric vehicle",
        "ev",
        "vehicle",
        "automobile"
    ]):
        return "Electric Vehicles"

    elif any(word in text for word in [
        "grid",
        "energy storage",
        "storage system"
    ]):
        return "Energy Storage Systems"

    elif any(word in text for word in [
        "phone",
        "smartphone",
        "laptop",
        "consumer electronics"
    ]):
        return "Consumer Electronics"

    else:
        return "General Applications"

df["Application Area"] = (
    df["combined_text"]
    .apply(classify_application)
)

print("\nPerforming final cleanup...")

df.drop(columns=["combined_text"], inplace=True)

df.reset_index(drop=True, inplace=True)

df.sort_values(
    by="Publication Year",
    ascending=False,
    inplace=True
)

df.to_csv(OUTPUT_FILE, index=False)

print("\n" + "=" * 60)
print("FINAL DATASET VALIDATION")
print("=" * 60)

print(f"\nFinal Dataset Shape: {df.shape}")

print("\nCountries Covered:")
print(df["Country"].value_counts())

print(
    f"\nYear Range: "
    f"{df['Publication Year'].min()} - "
    f"{df['Publication Year'].max()}"
)

print("\nTop Technology Categories:")
print(df["Technology Category"].value_counts())

print("\nTop Application Areas:")
print(df["Application Area"].value_counts())

print("\nTop Assignees:")
print(df["Primary Assignee"].value_counts().head(10))

print("\nFINAL DATASET SAVED SUCCESSFULLY")
print(f"Saved To: {OUTPUT_FILE}")

print("\n" + "=" * 60)
print("PREPROCESSING COMPLETED")
print("=" * 60)