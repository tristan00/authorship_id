from pathlib import Path

WORKERS = 20
CLAIM_LINES = 200
SAMPLE_SEED = 0
LABEL_MODEL = "gemma4-26b-a4b-nvfp4"
LABEL_PROMPT = "profile"
STRENGTHS = Path(r"D:\reddit_data\models\claim_consolidation.json")
STRENGTH_PRIOR = 1
SUBREDDIT_WEIGHT = 5
SUBREDDIT_SUPPORT = 5
