import uuid

from app.utils import clean_text, clean_value
from .store import (
    db_find_facts, db_add_fact, db_delete_facts,
    db_get_collection, db_set_collection, db_list_collections,
    db_get_aliases, db_set_alias,
)
from .resolver import resolve_entity
from .context import context


def _normalize_fact(subject, relation, object_):
    return clean_text(subject), clean_text(relation), clean_value(object_)


def _normalize_collection(owner, name, items):
    return (
        clean_text(owner),
        clean_text(name),
        [clean_value(i) for i in items if clean_value(i)]
    )


def _update_fact_context(results):
    if results:
        context["last_entity"]   = results[-1]["subject"]
        context["last_fact_id"]  = results[-1]["id"]
        context["last_subject"]  = results[-1]["subject"]
        context["last_relation"] = results[-1]["relation"]
        context["last_results"]  = results
    else:
        context["last_results"] = []


def _update_collection_context(owner, name):
    context["last_collection_owner"] = clean_text(owner)
    context["last_collection_name"]  = clean_text(name)


# ── FACTS ────────────────────────────────────────────────────

def add_fact(subject, relation, object_):
    subject, relation, object_ = _normalize_fact(subject, relation, object_)

    existing = db_find_facts(subject=subject, relation=relation, object_=object_)
    if existing:
        _update_fact_context(existing)
        return existing[0]

    fact = db_add_fact(subject, relation, object_)
    _update_fact_context([fact])
    return fact


def find_facts(subject=None, relation=None, object_=None):
    subject  = clean_text(subject)  if subject  else None
    relation = clean_text(relation) if relation else None
    object_  = clean_value(object_) if object_  else None

    results = db_find_facts(subject=subject, relation=relation, object_=object_)
    _update_fact_context(results)
    return results


def delete_facts(subject=None, relation=None, object_=None):
    subject  = clean_text(subject)  if subject  else None
    relation = clean_text(relation) if relation else None
    object_  = clean_value(object_) if object_  else None

    deleted = db_delete_facts(subject=subject, relation=relation, object_=object_)
    _update_fact_context(deleted)
    return deleted


def replace_fact(subject, relation, new_object):
    subject    = clean_text(subject)
    relation   = clean_text(relation)
    new_object = clean_value(new_object)

    deleted = delete_facts(subject=subject, relation=relation)
    added   = add_fact(subject, relation, new_object)
    return {"deleted": deleted, "added": added}


def dump_subject(subject):
    return find_facts(subject=clean_text(subject))


def resolve_and_find(subject=None, relation=None, object_=None):
    resolved = resolve_entity(subject) if subject else None
    return find_facts(subject=resolved, relation=relation, object_=object_)


def list_entities():
    results = db_find_facts()
    return sorted(set(f["subject"] for f in results if f["subject"] != "user"))


# ── COLLECTIONS ──────────────────────────────────────────────

def set_collection(owner, name, items):
    owner, name, items = _normalize_collection(owner, name, items)

    seen = set()
    clean_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            clean_items.append(item)

    col = db_set_collection(owner, name, clean_items)
    _update_collection_context(owner, name)
    return col


def get_collection(owner, name):
    owner = clean_text(owner)
    name  = clean_text(name)
    col   = db_get_collection(owner, name)
    if col:
        _update_collection_context(owner, name)
    return col


def list_collections(owner=None):
    return db_list_collections(owner=clean_text(owner) if owner else None)


def add_collection_item(owner, name, item):
    owner = clean_text(owner)
    name  = clean_text(name)
    item  = clean_value(item)

    col = db_get_collection(owner, name)
    if col:
        if item not in col["items"]:
            col["items"].append(item)
            db_set_collection(owner, name, col["items"])
        _update_collection_context(owner, name)
        return db_get_collection(owner, name)

    return set_collection(owner, name, [item])


def remove_collection_item(owner, name, item=None, index=None):
    owner = clean_text(owner)
    name  = clean_text(name)
    item  = clean_value(item) if item is not None else None

    col = db_get_collection(owner, name)
    if not col:
        return None

    removed = None
    items   = col["items"]

    if index is not None:
        if 0 <= index < len(items):
            removed = items.pop(index)
    elif item is not None:
        if item in items:
            items.remove(item)
            removed = item

    if removed is not None:
        db_set_collection(owner, name, items)

    _update_collection_context(owner, name)
    return removed


def replace_collection_item(owner, name, old_item, new_item):
    owner    = clean_text(owner)
    name     = clean_text(name)
    old_item = clean_value(old_item)
    new_item = clean_value(new_item)

    col = db_get_collection(owner, name)
    if not col or old_item not in col["items"]:
        return None

    idx = col["items"].index(old_item)
    col["items"][idx] = new_item

    seen    = set()
    deduped = []
    for i in col["items"]:
        if i not in seen:
            seen.add(i)
            deduped.append(i)

    db_set_collection(owner, name, deduped)
    _update_collection_context(owner, name)
    return db_get_collection(owner, name)


def delete_collection(owner, name):
    owner = clean_text(owner)
    name  = clean_text(name)

    col = db_get_collection(owner, name)
    if not col:
        return None

    from .store import _conn
    with _conn() as con:
        con.execute(
            "DELETE FROM collections WHERE owner = ? AND name = ?",
            (owner, name)
        )

    _update_collection_context(owner, name)
    return col


# ── ALIASES ──────────────────────────────────────────────────

def add_alias(alias, canonical):
    return db_set_alias(clean_text(alias), clean_text(canonical))


def get_aliases():
    return db_get_aliases()