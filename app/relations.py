from .utils import clean_text

REL_NAME         = "name"
REL_AGE          = "age"
REL_RELATIONSHIP = "relationship"
REL_BIRTHDAY     = "birthday"
REL_OCCUPATION   = "occupation"
REL_LOCATION     = "location"
REL_NATIONALITY  = "nationality"
REL_NICKNAME     = "nickname"
REL_PHONE        = "phone"
REL_EMAIL        = "email"

RELATIONS = {
    REL_NAME:         {"display": "name",         "multi": False, "kind": "attribute"},
    REL_AGE:          {"display": "age",           "multi": False, "kind": "attribute"},
    REL_RELATIONSHIP: {"display": "relationship",  "multi": False, "kind": "attribute"},
    REL_BIRTHDAY:     {"display": "birthday",      "multi": False, "kind": "attribute"},
    REL_OCCUPATION:   {"display": "occupation",    "multi": False, "kind": "attribute"},
    REL_LOCATION:     {"display": "location",      "multi": False, "kind": "attribute"},
    REL_NATIONALITY:  {"display": "nationality",   "multi": False, "kind": "attribute"},
    REL_NICKNAME:     {"display": "nickname",      "multi": True,  "kind": "attribute"},
    REL_PHONE:        {"display": "phone number",  "multi": False, "kind": "contact"},
    REL_EMAIL:        {"display": "email address", "multi": False, "kind": "contact"},
}


def relation_display(relation: str):
    relation = clean_text(relation)
    return RELATIONS.get(relation, {}).get("display", relation.replace("_", " "))


def is_known_relation(relation: str):
    relation = clean_text(relation)
    return relation in RELATIONS