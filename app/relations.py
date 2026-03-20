from .utils import clean_text


REL_NAME = "name"
REL_AGE = "age"
REL_RELATIONSHIP = "relationship"


RELATIONS = {
    REL_NAME: {
        "display": "name",
        "multi": False,
        "kind": "attribute",
    },
    REL_AGE: {
        "display": "age",
        "multi": False,
        "kind": "attribute",
    },
    REL_RELATIONSHIP: {
        "display": "relationship",
        "multi": False,
        "kind": "attribute",
    },
}


def relation_display(relation: str):
    relation = clean_text(relation)
    return RELATIONS.get(relation, {}).get("display", relation.replace("_", " "))


def is_known_relation(relation: str):
    relation = clean_text(relation)
    return relation in RELATIONS