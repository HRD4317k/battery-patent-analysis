"""Clean and enrich raw patent data using NLP-based tagging."""

import pandas as pd
import numpy as np
import os
import re
import logging
from tqdm import tqdm

# NLTK pieces for tokenizing and lemmatizing text.
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INPUT_PATH = os.path.join("data", "raw", "raw_patents.csv")
OUTPUT_PATH = os.path.join("data", "cleaned", "cleaned_patents.csv")

# Download missing NLTK resources once, quietly.
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    logging.info("Downloading required NLTK resources...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)

# Domain keyword maps used for tagging.
TECH_ONTOLOGY = {
    "Thermal & Safety": ["thermal", "cooling", "heat", "fire", "safety", "flame", "temperature", "dissipation"],
    "Battery Management (BMS)": ["bms", "management system", "state of charge", "monitoring", "circuit", "sensor", "balancing", "measurement"],
    "Pack & Structural": ["housing", "pack", "module", "enclosure", "structure", "chassis", "container", "casing"],
    "Manufacturing & Equipment": ["manufacturing", "machine", "die", "welding", "assembly", "production", "packaging", "machining", "fabrication"],
    "Electrodes & Materials": ["cathode", "anode", "electrode", "electrolyte", "separator", "alloy", "material", "binder"],
    "Solid-State & Advanced": ["solid state", "solid-state", "solid electrolyte", "sodium", "na-ion", "sulfide"],
    "Lithium-Based Chemistry": ["lithium", "li-ion", "lfp", "nmc", "lithium-ion"],
    "Recycling & Recovery": ["recycling", "recovery", "extraction", "second life", "reusing", "hydrometallurgical"],
    "Charging Tech": ["charging", "plug", "connector", "socket", "fast charge", "wireless charging"]
}

APP_ONTOLOGY = {
    "Grid & Infrastructure": ["grid", "bess", "energy storage", "power plant", "transformer", "distribution", "station"],
    "Medical & Healthcare": ["medical", "medicine", "postoperative", "health", "ultrasonic", "surgery", "implant"],
    "Consumer Electronics": ["mobile", "wearable", "phone", "laptop", "display", "light emitting", "consumer device"],
    "Electric Vehicles": ["vehicle", "ev", "automotive", "car", "electric vehicle", "transport", "powertrain", "scooter"]
}

class NLPPpatentTagger:
    """Normalize text and score topic categories."""
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
    def _normalize_text(self, text: str) -> str:
        """Tokenizes, removes stopwords, and lemmatizes a string."""
        if pd.isna(text):
            return ""
        
        # Keep text simple before tokenization.
        text = re.sub(r'[^\w\s]', ' ', str(text).lower())
        
        tokens = word_tokenize(text)
        
        cleaned_tokens = [
            self.lemmatizer.lemmatize(word) 
            for word in tokens 
            if word not in self.stop_words and len(word) > 1
        ]
        
        return " ".join(cleaned_tokens)

    def _score_categories(self, normalized_text: str, ontology: dict) -> str:
        """
        Calculates a score for each category based on keyword occurrences 
        in the normalized text. Returns the highest-scoring category.
        """
        if not normalized_text:
            return "Other / General"
            
        scores = {category: 0 for category in ontology.keys()}
        
        for category, keywords in ontology.items():
            for kw in keywords:
                # Normalize keyword too so matching is fair.
                norm_kw = self.lemmatizer.lemmatize(kw.lower())
                occurrences = len(re.findall(rf'\b{re.escape(norm_kw)}\b', normalized_text))
                scores[category] += occurrences
                
        best_category = max(scores, key=scores.get)
        
        if scores[best_category] == 0:
            return "Other / General"
            
        return best_category

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies the NLP pipeline to the DataFrame."""
        logging.info("Initializing NLP text normalization (Lemmatization & Tokenization)...")
        
        # Use title + abstract together for better tagging context.
        combined_text = df['Title'].fillna("") + " " + df['Abstract'].fillna("")
        
        tqdm.pandas(desc="Normalizing Text")
        normalized_series = combined_text.progress_apply(self._normalize_text)
        
        logging.info("Scoring and tagging Technology Categories...")
        tqdm.pandas(desc="Tagging Tech")
        df['Technology Category'] = normalized_series.progress_apply(
            lambda x: self._score_categories(x, TECH_ONTOLOGY)
        )
        
        logging.info("Scoring and tagging Application Areas...")
        tqdm.pandas(desc="Tagging Apps")
        df['Application Area'] = normalized_series.progress_apply(
            lambda x: self._score_categories(x, APP_ONTOLOGY)
        )
        
        return df

class PatentDataCleaner:
    
    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.df = None
        self.tagger = NLPPpatentTagger()

    def load_data(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file missing: {self.input_path}")
        self.df = pd.read_csv(self.input_path)
        logging.info(f"Data loaded successfully: {self.df.shape[0]} rows, {self.df.shape[1]} columns.")

    def clean_and_deduplicate(self):
        initial_count = len(self.df)
        self.df = self.df.drop_duplicates(subset=["Lens ID"], keep="first")
        self.df = self.df.drop_duplicates(subset=["Title"], keep="first") 
        dropped = initial_count - len(self.df)
        logging.info(f"Deduplication complete. Removed {dropped} duplicate records.")
        
        # Keep year clean and consistent.
        self.df['Publication Year'] = self.df['Publication Year'].fillna(0).astype(int)
        
        self.df = self.df.rename(columns={
            "Jurisdiction": "Country",
            "Applicants": "Assignee (Applicant)"
        })

    def extract_entities(self):
        """Extracts primary business entities for firm-level analysis."""
        logging.info("Extracting and normalizing Primary Assignees...")
        
        def get_primary(entity_str):
            if pd.isna(entity_str) or str(entity_str).strip() == "":
                return "Unknown"
            return str(entity_str).split(";;")[0].strip()
            
        self.df['Primary Assignee'] = self.df['Assignee (Applicant)'].apply(get_primary)
        
        # Strip common company suffixes so assignees group better.
        corp_suffixes = r"(?i)\b(inc|ltd|llc|corp|corporation|co|limited|gmbh|sa|nv)\b\.?"
        self.df['Primary Assignee'] = self.df['Primary Assignee'].str.replace(corp_suffixes, "", regex=True).str.strip()

    def run_pipeline(self):
        logging.info("Starting Transformation Pipeline...")
        self.load_data()
        self.clean_and_deduplicate()
        self.extract_entities()
        
        self.df = self.tagger.extract_features(self.df)
        
        final_columns = [
            "Lens ID", "Country", "Publication Date", "Publication Year", 
            "Title", "Assignee (Applicant)", "Primary Assignee",
            "Technology Category", "Application Area", "Abstract", "URL"
        ]
        self.df = self.df[final_columns]
        
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        self.df.to_csv(self.output_path, index=False, encoding="utf-8")
        logging.info(f"Pipeline complete. Cleaned data saved to: {self.output_path}")

        print("\n" + "="*65)
        print("  VERIFICATION PREVIEW (Top 10 Scored Classifications)")
        print("="*65)
        preview = self.df[['Title', 'Technology Category', 'Application Area']].head(10)
        # Shorten long titles so the console table stays readable.
        preview['Title'] = preview['Title'].apply(lambda x: (str(x)[:40] + '...') if len(str(x)) > 40 else x)
        print(preview.to_string(index=False))


if __name__ == "__main__":
    cleaner = PatentDataCleaner(INPUT_PATH, OUTPUT_PATH)
    cleaner.run_pipeline()