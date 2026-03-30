from app.core import process_input
from app.memory.store import init_db
from app.personality import say
from app.actions import load_pending_reminders


def main():
    init_db()
    load_pending_reminders()
    print("Jarvis:\nHello! I am your assistant. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() == "exit":
                print(f"\nJarvis:\n{say('farewell')}\n")
                break
            answer = process_input(user_input)
            print(f"\nJarvis:\n{answer}\n")
        except KeyboardInterrupt:
            print(f"\nJarvis:\n{say('farewell')}\n")
            break


if __name__ == "__main__":
    main()