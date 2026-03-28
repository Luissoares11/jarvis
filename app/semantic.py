import re
from difflib import get_close_matches

from .memory.context import context


_SOCIAL = {
    "thanks", "thank you", "ok", "okay", "cool", "got it",
    "sure", "yes", "no", "nope", "yep", "alright", "nice",
    "great", "perfect", "awesome", "understood", "fine",
    "yeah","nah","confirm", "cancel", "correct", 
    "do it","update it", "keep it", "leave it",
}

_ORDINALS = {"1": "first", "2": "second", "3": "third"}

_MATH_PREFIXES = (
    "calculate:", "calc:", "compute:",
    "derivative of", "differentiate",
    "integral of", "integrate",
    "solve:", "solve ",
    "limit of", "lim of",
    "plot ", "graph ", "draw ",
)



def _ordinal_to_word(match):
    n = match.group(1)
    return f"remove {_ORDINALS.get(n, 'last')}"


def _item_number_to_word(match):
    n = match.group(1)
    return f"remove {_ORDINALS.get(n, 'last')}"

def _resolve_it_update(match):
    value = match.group(1)
    last_relation = context.get("last_relation")
    last_entity = context.get("last_entity")

    # figure out who we're updating
    if last_entity and last_entity != "user":
        subject = last_entity
    else:
        subject = "my"

    if last_relation:
        return f"change {subject} {last_relation} to {value}"

    return f"change {subject} age to {value}"

SYNONYM_MAP = [
    # typo tolerance
    (r"\bwhts\b",                                    "whats"),
    (r"\bwaht\b",                                    "what"),
    (r"\bwath\b",                                    "what"),

    # query verbs
    (r"\bwhat devices do i (use|have|own)\b",        "what are the devices i use"),
    (r"\bwhich devices do i (use|have|own)\b",       "what are the devices i use"),
    (r"\bmy devices\??$",                            "what are the devices i use"),
    (r"\bshow me my (.+)$",                          r"what are my \1"),
    (r"\blist my (.+)$",                             r"what are my \1"),
    (r"\bdo you know (.+)\??$",                      r"what are \1"),

    # age queries
    (r"\bhow old am i\??$",                          "how old am i"),
    (r"\bwhat(?:'s| is) my age\??$",                 "what is my age"),
    (r"\bage of (.+)\??$",                           r"how old is \1"),

    # store verbs
    (r"\bremember my (.+?) is (.+)$",                r"my \1 is \2"),
    (r"\bsave that (.+)$",                           r"remember that \1"),
    (r"\bkeep in mind that (.+)$",                   r"remember that \1"),
    (r"\bnote that (.+)$",                           r"remember that \1"),

    # delete verbs
    (r"\bforget about (.+)$",                        r"forget \1"),
    (r"\berase (.+)$",                               r"forget \1"),
    (r"\bremove (.+?) from memory$",                 r"forget \1"),

    # person relations
    (r"\b(.+?) is my (girlfriend|boyfriend|wife|husband|brother|sister|friend|partner)\b",
                                                     r"\1 is my \2"),

    # collection positional
    (r"\b(?:remove|delete) (?:the )?(\d+)(?:st|nd|rd|th)(?: one)?$", _ordinal_to_word),
    (r"\b(?:remove|delete) (?:the )?first one$",     "remove first"),
    (r"\b(?:remove|delete) (?:the )?last one$",      "remove last"),
    (r"\b(?:remove|delete) item (\d+)$",             _item_number_to_word),

    # updating information
    (r"^update (?:it|this|that) to (.+)$",  _resolve_it_update),
    (r"^change (?:it|this|that) to (.+)$",  _resolve_it_update),
    (r"^set (?:it|this|that) to (.+)$",     _resolve_it_update),
    (r"^make (?:it|this|that) (.+)$",       _resolve_it_update),

    # computation synonyms — add to SYNONYM_MAP
    (r"^what is (\d[\d\s\+\-\*\/\^\(\)\.]+)$",  r"calculate: \1"),
    (r"^how much is (.+)\??$",                    r"calculate: \1"),
    (r"^whats (\d[\d\s\+\-\*\/\^\(\)\.]+)\??$",  r"calculate: \1"),
    (r"^diff (.+) wrt ([a-z])$",                  r"differentiate \1 with respect to \2"),
    (r"^d/d([a-z]) of (.+)$",                     r"derivative of \2 with respect to \1"),
    (r"^(\d+(?:\.\d+)?) ([a-z]+) in ([a-z]+)$",  r"\1 \2 to \3"),
]


COLLECTION_SYNONYMS = {
    "gadgets":    "devices i use",
    "gear":       "devices i use",
    "tech":       "devices i use",
    "stuff":      "things",
    "belongings": "things",
}


def _apply_synonym_map(text: str) -> str:
    for pattern, replacement in SYNONYM_MAP:
        if callable(replacement):
            text, n = re.subn(pattern, replacement, text)
        else:
            text, n = re.subn(pattern, replacement, text)
        if n:
            break
    return text


def _apply_collection_synonyms(text: str) -> str:
    for synonym, canonical in COLLECTION_SYNONYMS.items():
        if synonym in text:
            text = text.replace(synonym, canonical)
    return text

def resolve_followup(text: str) -> str:
    t = text.lower().strip()
    last_entity = context.get("last_entity")

    if not last_entity:
        return text

    # how old is she/he/they → how old is <entity>
    followup_age = [
        r"^how old is (she|he|they|it)$",
        r"^what(?:'s| is) (her|his|their|its) age$",
        r"^(her|his|their) age\??$",
        r"^and (her|his|their) age\??$",
        r"^what about (her|his|their) age\??$",
    ]
    for pattern in followup_age:
        if re.match(pattern, t):
            return f"how old is {last_entity}"

    # who is she/he → who is <entity>
    followup_who = [
        r"^who is (she|he|they)$",
        r"^and who is (she|he|they)$",
    ]
    for pattern in followup_who:
        if re.match(pattern, t):
            return f"who is {last_entity}"

    # what about her/him → who is <entity>
    if re.match(r"^what about (her|him|them)$", t):
        return f"who is {last_entity}"

    # and her/his name? → who is <entity>
    if re.match(r"^(?:and )?(?:her|his|their) name\??$", t):
        return f"who is {last_entity}"

    return text


def fuzzy_collection_name(name: str, known_names: list[str]) -> str:
    matches = get_close_matches(name, known_names, n=1, cutoff=0.6)
    return matches[0] if matches else name


def normalize(text: str) -> str:
    t = text.lower().strip()

    if t in _SOCIAL:
        return t

    # skip all transformations for math input
    if any(t.startswith(p) for p in _MATH_PREFIXES):
        return t

    t = resolve_followup(t)
    t = _apply_synonym_map(t)
    t = _apply_collection_synonyms(t)
    return t