context = {
    # entity tracking
    "last_entity":           None,
    "last_entity_facts":     [],
    "last_subject":          None,
    "last_relation":         None,
    "last_fact_id":          None,
    "last_results":          [],

    # collection tracking
    "last_collection_owner": None,
    "last_collection_name":  None,

    # action tracking
    "last_action":           None,

    # conversation tracking
    "last_question_type":    None,
    "entity_stack":          [],

    # reasoning ← new
    "pending_conflict":      None,
}