from .memory.api import find_facts, replace_fact
from .memory.context import context
from .relations import REL_AGE, REL_RELATIONSHIP, REL_NAME


# ── conflict detection ────────────────────────────────────────

def check_conflict(subject: str, relation: str, new_object: str):
    """
    Check if a new fact conflicts with an existing one.
    Returns the existing fact if conflict found, None otherwise.
    """
    existing = find_facts(subject=subject, relation=relation)
    if not existing:
        return None

    current = existing[0]["object"]
    if current != new_object:
        return existing[0]

    return None


def store_pending_conflict(subject: str, relation: str, new_object: str, existing_object: str):
    """Store a conflict in context waiting for user confirmation."""
    context["pending_conflict"] = {
        "subject":   subject,
        "relation":  relation,
        "new":       new_object,
        "existing":  existing_object,
    }


def resolve_pending_conflict(confirmed: bool):
    """
    Resolve a pending conflict.
    If confirmed, apply the update. If not, keep the existing fact.
    """
    pending = context.get("pending_conflict")
    if not pending:
        return None

    context["pending_conflict"] = None

    if confirmed:
        replace_fact(pending["subject"], pending["relation"], pending["new"])
        return "confirmed"

    return "rejected"


def has_pending_conflict():
    return bool(context.get("pending_conflict"))


# ── implicit fact storage ─────────────────────────────────────

def infer_implicit_facts(subject: str, relation: str, object_: str):
    """
    When a fact is stored, check if we can infer and store additional facts.
    Returns list of any new facts inferred.
    """
    inferred = []

    # if we just stored an age for someone,
    # and that someone is an alias target, nothing extra needed
    # but if they have a relationship stored, log the inference
    if relation == REL_AGE:
        rel_facts = find_facts(subject=subject, relation=REL_RELATIONSHIP)
        if rel_facts:
            relationship = rel_facts[0]["object"]
            inferred.append({
                "type":     "implicit_age",
                "subject":  subject,
                "via":      f"your {relationship}",
                "object":   object_,
            })

    # if we just stored a relationship for someone,
    # check if they already have an age — surface it
    if relation == REL_RELATIONSHIP:
        age_facts = find_facts(subject=subject, relation=REL_AGE)
        if age_facts:
            inferred.append({
                "type":     "implicit_relationship_age",
                "subject":  subject,
                "relation": REL_AGE,
                "object":   age_facts[0]["object"],
                "via":      object_,
            })

    return inferred


# ── transitive inference ──────────────────────────────────────

def resolve_transitive(subject: str, relation: str):
    """
    Try to answer a query by chaining through known facts.
    Example: "how old is my girlfriend"
      → find who "my girlfriend" is via aliases/relationship facts
      → find their age
    Returns the resolved fact or None.
    """
    from .memory.api import find_facts as ff

    # look up subject as a relationship value
    # e.g. subject = "my girlfriend" → find who has relationship = "girlfriend"
    rel_value = subject.replace("my ", "").strip()
    matches = ff(relation=REL_RELATIONSHIP, object_=rel_value)

    if len(matches) == 1:
        real_subject = matches[0]["subject"]
        facts = ff(subject=real_subject, relation=relation)
        if facts:
            return {
                "subject": real_subject,
                "via":     subject,
                "facts":   facts,
            }

    return None