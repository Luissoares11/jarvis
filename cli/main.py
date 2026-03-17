from app.core import process_input

def run():
    print("Jarvis: Hello! Type 'exit' to quit.")

    while True:
        user = input("You: ")

        if user.lower() == "exit":
            break

        response = process_input(user)
        print("Jarvis:", response)

if __name__ == "__main__":
    run()