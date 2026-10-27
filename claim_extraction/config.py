from pathlib import Path

FIELDS = ("age", "birth_year", "generation", "gender", "sexual_orientation", "race_ethnicity", "nationality", "language", "religion",
          "residence_country", "residence_state", "residence_city", "origin_country", "origin_state", "origin_city",
          "height", "weight", "income", "education", "education_subject", "occupation", "employment_status",
          "marital_status", "relationship_status", "parental_status", "mental_health", "political_compass", "political_ideology")
NUMERIC = {"age": (13, 100), "birth_year": (1920, 2013), "height": (120, 230), "weight": (30, 300), "income": (1000, 10_000_000)}
READABLE = ("available", "title_only")
ANNOTATIONS = Path(r"D:\reddit_data\annotations")
SAMPLE_TEXTS = 100_000
SAMPLE_MAX_BYTES = 10_000
SAMPLE_PERCENT = 0.05
SPLITS = (("train", 90), ("validation", 95), ("test", 100))
