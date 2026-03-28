from .store import load_store
from .context import context
from app.utils import clean_text
from app.relations import REL_RELATIONSHIP

_PRONOUNS_FEMALE  = {"her", "she", "hers"}
_PRONOUNS_MALE    = {"his", "he", "him"}
_PRONOUNS_NEUTRAL = {"them", "their", "they", "it", "its"}
_PRONOUNS_SELF    = {"me", "myself", "i", "my"}
_ALL_PRONOUNS     = _PRONOUNS_FEMALE | _PRONOUNS_MALE | _PRONOUNS_NEUTRAL

_ENTITY_STACK_SIZE = 3


def push_entity(name: str):
    """Record an entity as the most recently mentioned."""
    if not name or name == "user":
        return

    stack = context.get("entity_stack") or []

    if stack and stack[0] == name:
        return  # already on top, no change

    if name in stack:
        stack.remove(name)

    stack.insert(0, name)
    context["entity_stack"] = stack[:_ENTITY_STACK_SIZE]
    context["last_entity"] = name


def _resolve_pronoun():
    """Return the most recently mentioned non-user entity, or None."""
    stack = context.get("entity_stack") or []
    if stack:
        return stack[0]
    if context.get("last_entity"):
        return context["last_entity"]
    return None


def resolve_entity(name: str):
    if not name:
        return None

    data = load_store()
    aliases = data["aliases"]
    ref = clean_text(name)

    # pronouns → last known entity
    if ref in _ALL_PRONOUNS:
        resolved = _resolve_pronoun()
        return resolved if resolved else ref

    # self-references → user
    if ref in _PRONOUNS_SELF:
        return "user"

    # alias lookup
    if ref in aliases:
        resolved = aliases[ref]
        push_entity(resolved)
        return resolved

    # direct name
    push_entity(ref)
    return ref


def infer_entity_from_relation_target(target_value: str):
    from .api import find_facts

    value = clean_text(target_value)
    matches = find_facts(relation=REL_RELATIONSHIP, object_=value)

    if len(matches) == 1:
        entity = matches[0]["subject"]
        push_entity(entity)
        return entity

    return None