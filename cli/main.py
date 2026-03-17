from app.core import process_input


def main():
    print("Jarvis: Hello! I am your assistant. Type 'exit' to quit.")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            print("Jarvis: Goodbye!")
            break

        answer = process_input(user_input)
        print("Jarvis:", answer)


if __name__ == "__main__":
    main()