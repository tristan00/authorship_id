CLAIMS = "\n\n<claims>\n{text}\n</claims>"
PROMPTS = {
    "profile": "Below are the claims found about one Reddit author, one per line: the subreddit it came from, the source (text means the author wrote it in a "
               "post or comment, flair means it comes from their user flair), and field: value. Write the author's most likely value for each field that "
               "appears, one field: value line per field." + CLAIMS,
}
