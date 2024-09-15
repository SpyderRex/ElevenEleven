import time
import random
from colorama import Fore, Style, init
from chat11_11 import Chat11_11

# List of color options excluding white and black
colors = [
    Fore.RED, Fore.GREEN, Fore.BLUE, Fore.CYAN, Fore.MAGENTA, Fore.LIGHTRED_EX, Fore.LIGHTGREEN_EX, Fore.LIGHTBLACK_EX,
    Fore.LIGHTBLUE_EX, Fore.LIGHTCYAN_EX, Fore.LIGHTMAGENTA_EX
]

def print_slowly(text, color):
    for word in text.split():
        print(color + word + Style.RESET_ALL, end=' ', flush=True)
        time.sleep(0.11)
    print()

def main():
    # Initialize the chat
    chat = Chat11_11()

    # Initialize colorama
    init(autoreset=True)

    # Continuous chat loop
    while True:
        user_message = input(Fore.GREEN + "You: " + Style.RESET_ALL)
        if user_message.lower() in ['exit', 'quit', 'bye']:
            print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
            break
        
        response = chat.send_message(user_message)
        
        # Randomly select colors for response and name
        name_color = random.choice(colors)
        response_color = random.choice(colors)
        
        print(name_color + "ElevenEleven: ", end='')
        print_slowly(response, response_color)

if __name__ == "__main__":
    main()