import re

def satyacode_detect(text):
    text = text.lower()

    score = {
        "truth": 0,
        "lie": 0,
        "confusion": 0,
        "anger": 0,
        "love": 0,
        "hidden": 0
    }

    # --- Truth / Lie ---
    if re.search(r"\b(i'?m fine|okay|all good)\b", text):
        score["lie"] += 2
        score["hidden"] += 2

    if re.search(r"\b(honestly|actually|truth)\b", text):
        score["truth"] += 2

    # --- Emotion ---
    if re.search(r"\b(angry|frustrated|bad service|worst|delay)\b", text):
        score["anger"] += 2

    if re.search(r"\b(love|like|appreciate)\b", text):
        score["love"] += 2

    # --- Confusion ---
    if re.search(r"\b(confused|not sure|maybe|idk)\b", text):
        score["confusion"] += 2

    # --- Hidden intent ---
    if "but" in text or "..." in text:
        score["hidden"] += 1

    # --- Build Code ---
    code = ""

    if score["lie"] > score["truth"]:
        code += "✕ "
    elif score["truth"] > 0:
        code += "○ "
    else:
        code += "◐ "

    if score["anger"] > 0:
        code += "⚡ "
    elif score["love"] > 0:
        code += "♥ "
    elif score["confusion"] > 0:
        code += "∆∆ "
    else:
        code += "∆ "

    if score["hidden"] > 0:
        code += "🔒 "

    return code.strip()