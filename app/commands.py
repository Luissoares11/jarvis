from .memory import add_item, remove_item

def handle_add(topic, item):
    add_item(topic, item)
    return f"Added '{item}' to '{topic}'."

def handle_remove(topic, item):
    success = remove_item(topic, item)

    if success:
        return f"Removed '{item}' from '{topic}'."
    return "Item not found."