import re

from .patterns import positioned

COMPASS_SUBREDDIT = "politicalcompassmemes"
MBTI = re.compile(r"(?<![A-Za-z])([IE][NS][TF][JP])(?:-[AT])?(?![A-Za-z])")
COMPASS = re.compile(r"(?i)(?:^|[\s:-])(?:chad\s+)?(?:(auth|lib)[-\s]?)?(left|center|centre|right|centrist)\s*$")


def compass(flair):
    if not (match := COMPASS.search(flair)):
        return None
    axis, side = (match.group(1) or "").lower(), match.group(2).lower().replace("centre", "center")
    if side in ("center", "centrist"):
        return f"{axis}-center" if axis else "centrist"
    return f"{axis}-{side}" if axis else side


def flair_claims(subreddit, flair):
    found = {pair for pair in positioned(flair)}
    found |= {("personality_type", match.group(1)) for match in MBTI.finditer(flair)}
    if subreddit == COMPASS_SUBREDDIT and (side := compass(flair)):
        found.add(("political_compass", side))
    return found
