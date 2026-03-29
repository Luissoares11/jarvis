def make_context() -> dict:
    return {
        "last_entity":              None,
        "last_entity_facts":        [],
        "last_subject":             None,
        "last_relation":            None,
        "last_fact_id":             None,
        "last_results":             [],
        "last_collection_owner":    None,
        "last_collection_name":     None,
        "last_action":              None,
        "last_question_type":       None,
        "entity_stack":             [],
        "pending_conflict":         None,
        "pending_learning":         None,
        "pending_learning_action":  None,
    }

# keep this for CLI compatibility — CLI uses a single persistent context
context = make_context()