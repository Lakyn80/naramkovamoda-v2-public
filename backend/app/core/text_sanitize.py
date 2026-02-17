import re


_BANNED_WORD_RE = re.compile(r"\b(chlup\w*|chlupat\w*)\b", flags=re.IGNORECASE | re.UNICODE)


def remove_banned_word_variants(text: str) -> str:
    """
    Remove any variants of the banned word from text.
    If a line becomes empty or just a bullet marker, drop it.
    """
    if not text:
        return text
    lines = text.splitlines()
    output: list[str] = []
    for line in lines:
        if not _BANNED_WORD_RE.search(line):
            output.append(line)
            continue
        cleaned = _BANNED_WORD_RE.sub("", line)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        if cleaned in ("-", "•", "*", "–"):
            continue
        if cleaned:
            output.append(cleaned)
    return "\n".join(output)
