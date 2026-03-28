from app.core import process_input
from app.memory.store import init_db


def main():
    init_db()

    print("Jarvis:\nHello! I am your assistant. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("\nJarvis:\nGoodbye!\n")
            break

        answer = process_input(user_input)
        print(f"\nJarvis:\n{answer}\n")


if __name__ == "__main__":
    main()