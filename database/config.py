from pathlib import Path

PG = Path(r"C:\Users\trist\pg\pgsql\bin")
DATA = Path(r"D:\reddit_data\postgres")
DUMPS = Path(r"D:\reddit_data\dumps")
LOGS = Path(r"D:\reddit_data\logs")
PORT = 5499
DSN = f"host=localhost port={PORT} dbname=reddit user=postgres"
NOT_PEOPLE = (r"^(|\[deleted\]|\[removed\]|automoderator|flairassistant|judgement_bot_aita|nostupidquestionsbot|moderatelyusefulbot|deltabot"
              r"|ukbot-nicolabot|flairchange_bot|basedcount_bot|repostsleuthbot|remindmebot|bot-sleuth-bot|amputatorbot|haikusbot|sneakpeekbot"
              r"|hi_im_dadbot|.*-modteam|.*[_-]bot)$")

PARSERS = 16
SCAN_WORKERS = 16
