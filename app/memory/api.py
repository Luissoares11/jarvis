import uuid

from app.utils import clean_text, clean_value
from .models import Fact, Collection
from .store import load_store, save_store
from .resolver import resolve_entity
from .context import context


def _normalize_fact(subject: str, relation: str, object_: str):
    return (
        clean_text(subject),
        clean_text(relation),
        clean_value(object_)
    )


def _normalize_collection(owner: str, name: str, items: list[str]):
    return (
        clean_text(owner),
        clean_text(name),
        [clean_value(item) for item in items if clean_value(item)]
    )


def _update_fact_context(results):
    if results:
        context["last_entity"] = results[-1]["subject"]
        context["last_fact_id"] = results[-1]["id"]
        context["last_subject"] = results[-1]["subject"]
        context["last_relation"] = results[-1]["relation"]
        context["last_results"] = results
    else:
        context["last_results"] = []


def _update_collection_context(owner: str, name: str):
    context["last_collection_owner"] = clean_text(owner)
    context["last_collection_name"] = clean_text(name)


# ---------- FACTS ----------

def add_fact(subject: str, relation: str, object_: str):
    data = load_store()
    facts = data["facts"]

    subject, relation, object_ = _normalize_fact(subject, relation, object_)

    for fact in facts:
        if (
            fact["subject"] == subject and
            fact["relation"] == relation and
            fact["object"] == object_
        ):
            _update_fact_context([fact])
            return fact

    new_fact = Fact(
        id=str(uuid.uuid4()),
        subject=subject,
        relation=relation,
        object=object_,
    ).to_dict()

    facts.append(new_fact)
    save_store(data)

    _update_fact_context([new_fact])
    return new_fact


def find_facts(subject=None, relation=None, object_=None):
    data = load_store()
    facts = data["facts"]

    subject = clean_text(subject) if subject else None
    relation = clean_text(relation) if relation else None
    object_ = clean_value(object_) if object_ else None

    results = []

    for fact in facts:
        if subject is not None and fact["subject"] != subject:
            continue
        if relation is not None and fact["relation"] != relation:
            continue
        if object_ is not None and fact["object"] != object_:
            continue
        results.append(fact)

    _update_fact_context(results)
    return results


def delete_facts(subject=None, relation=None, object_=None):
    data = load_store()
    facts = data["facts"]

    subject = clean_text(subject) if subject else None
    relation = clean_text(relation) if relation else None
    object_ = clean_value(object_) if object_ else None

    kept = []
    deleted = []

    for fact in facts:
        match = True

        if subject is not None and fact["subject"] != subject:
            match = False
        if relation is not None and fact["relation"] != relation:
            match = False
        if object_ is not None and fact["object"] != object_:
            match = False

        if match:
            deleted.append(fact)
        else:
            kept.append(fact)

    data["facts"] = kept
    save_store(data)

    _update_fact_context(deleted)
    return deleted


def replace_fact(subject: str, relation: str, new_object: str):
    subject = clean_text(subject)
    relation = clean_text(relation)
    new_object = clean_value(new_object)

    deleted = delete_facts(subject=subject, relation=relation)
    added = add_fact(subject, relation, new_object)

    return {
        "deleted": deleted,
        "added": added,
    }


def dump_subject(subject: str):
    subject = clean_text(subject)
    return find_facts(subject=subject)


def resolve_and_find(subject=None, relation=None, object_=None):
    resolved_subject = resolve_entity(subject) if subject else None
    return find_facts(subject=resolved_subject, relation=relation, object_=object_)


def list_entities():
    data = load_store()
    facts = data["facts"]

    subjects = sorted(set(f["subject"] for f in facts if f["subject"] != "user"))
    return subjects


# ---------- COLLECTIONS ----------

def set_collection(owner: str, name: str, items: list[str]):
    data = load_store()
    collections = data["collections"]

    owner, name, items = _normalize_collection(owner, name, items)

    seen = set()
    clean_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            clean_items.append(item)

    for collection in collections:
        if collection["owner"] == owner and collection["name"] == name:
            collection["items"] = clean_items
            save_store(data)
            _update_collection_context(owner, name)
            return collection

    new_collection = Collection(
        id=str(uuid.uuid4()),
        owner=owner,
        name=name,
        items=clean_items,
    ).to_dict()

    collections.append(new_collection)
    save_store(data)

    _update_collection_context(owner, name)
    return new_collection


def get_collection(owner: str, name: str):
    data = load_store()
    collections = data["collections"]

    owner = clean_text(owner)
    name = clean_text(name)

    for collection in collections:
        if collection["owner"] == owner and collection["name"] == name:
            _update_collection_context(owner, name)
            return collection

    return None


def list_collections(owner=None):
    data = load_store()
    collections = data["collections"]

    if owner is None:
        return collections

    owner = clean_text(owner)
    return [c for c in collections if c["owner"] == owner]


def add_collection_item(owner: str, name: str, item: str):
    data = load_store()
    collections = data["collections"]

    owner = clean_text(owner)
    name = clean_text(name)
    item = clean_value(item)

    for collection in collections:
        if collection["owner"] == owner and collection["name"] == name:
            if item not in collection["items"]:
                collection["items"].append(item)
                save_store(data)
            _update_collection_context(owner, name)
            return collection

    return set_collection(owner, name, [item])


def remove_collection_item(owner: str, name: str, item=None, index=None):
    data = load_store()
    collections = data["collections"]

    owner = clean_text(owner)
    name = clean_text(name)
    item = clean_value(item) if item is not None else None

    for collection in collections:
        if collection["owner"] == owner and collection["name"] == name:
            removed = None

            if index is not None:
                if 0 <= index < len(collection["items"]):
                    removed = collection["items"].pop(index)
            elif item is not None:
                if item in collection["items"]:
                    collection["items"].remove(item)
                    removed = item

            if removed is not None:
                save_store(data)

            _update_collection_context(owner, name)
            return removed

    return None


def replace_collection_item(owner: str, name: str, old_item: str, new_item: str):
    data = load_store()
    collections = data["collections"]

    owner = clean_text(owner)
    name = clean_text(name)
    old_item = clean_value(old_item)
    new_item = clean_value(new_item)

    for collection in collections:
        if collection["owner"] == owner and collection["name"] == name:
            if old_item not in collection["items"]:
                return None

            idx = collection["items"].index(old_item)
            collection["items"][idx] = new_item

            # dedupe while preserving order
            seen = set()
            deduped = []
            for item in collection["items"]:
                if item not in seen:
                    seen.add(item)
                    deduped.append(item)

            collection["items"] = deduped
            save_store(data)
            _update_collection_context(owner, name)
            return collection

    return None


def delete_collection(owner: str, name: str):
    data = load_store()
    collections = data["collections"]

    owner = clean_text(owner)
    name = clean_text(name)

    kept = []
    deleted = None

    for collection in collections:
        if collection["owner"] == owner and collection["name"] == name:
            deleted = collection
        else:
            kept.append(collection)

    data["collections"] = kept
    save_store(data)

    if deleted:
        _update_collection_context(owner, name)

    return deleted


# ---------- ALIASES ----------

def add_alias(alias: str, canonical: str):
    data = load_store()

    alias = clean_text(alias)
    canonical = clean_text(canonical)

    data["aliases"][alias] = canonical
    save_store(data)

    return {alias: canonical}


def get_aliases():
    data = load_store()
    return data["aliases"]