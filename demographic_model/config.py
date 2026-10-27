from pathlib import Path

ROOT = Path(r"D:\reddit_data\demographic_model\three_fold")
FOLDS = 3
PARTIAL = ("residence", "origin", "occupation", "education_subject", "political_compass", "political_ideology")
COMPLETE_HEADS = 50
PARAMETERS = {"width": 128, "dropout": 0.4564811903773219, "lr": 0.0007934426450883118, "weight_decay": 0.08092563341708463, "batch": 256, "mixtures": 3, "epochs": 12, "patience": 2, "seed": 719}
