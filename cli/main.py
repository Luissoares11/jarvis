from app.core import process_input


def main():
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