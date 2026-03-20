from .store import load_store
from .context import context
from app.utils import clean_text
from app.relations import REL_RELATIONSHIP


def resolve_entity(name: str):
    if not name:
        return None

    data = load_store()
    aliases = data["aliases"]
    ref = clean_text(name)

    if ref in ["her", "she", "his", "he", "them", "their"]:
        if context.get("last_entity"):
            return context["last_entity"]

    if ref in ["me", "myself", "i", "my"]:
        return "user"

    if ref in aliases:
        resolved = aliases[ref]
        context["last_entity"] = resolved
        return resolved

    context["last_entity"] = ref
    return ref


def infer_entity_from_relation_target(target_value: str):
    from .api import find_facts

    value = clean_text(target_value)
    matches = find_facts(relation=REL_RELATIONSHIP, object_=value)

    if len(matches) == 1:
        entity = matches[0]["subject"]
        context["last_entity"] = entity
        return entity

    return None