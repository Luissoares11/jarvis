context = {
    # entity tracking
    "last_entity":              None,
    "last_entity_facts":        [],   # full fact list from last entity query
    "last_subject":             None,
    "last_relation":            None,
    "last_fact_id":             None,
    "last_results":             [],

    # collection tracking
    "last_collection_owner":    None,
    "last_collection_name":     None,

    # action tracking
    "last_action":              None,

    # conversation tracking  ← new
    "last_question_type":       None, # "who" | "age" | "collection" | None
    "entity_stack":             [],   # history of last 3 entities mentioned
}