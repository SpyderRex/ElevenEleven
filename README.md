# ElevenEleven

ElevenEleven is an AI spiritual philosopher and confidant. It leverages the Llama3 model from the Groq API to provide insightful conversations. The program saves chat history in a local SQLite database and uses a simple Retrieval-Augmented Generation (RAG) method with Spacy to enhance the quality of the responses.

## Features
- **Llama3 Model**: Powered by the Llama3 model from the Groq API for AI-based conversations.
- **Chat History**: Automatically saves chat history to a local SQLite database.
- **RAG Method**: Utilizes a simple Retrieval-Augmented Generation (RAG) method with Spacy for more accurate and meaningful dialogue.
- **Function Calling**: Includes function calling abilities. The current function can provide the current time in Central Standard Time (CST).

## Requirements
- A Groq API key.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SpyderRex/ElevenEleven
cd ElevenEleven
```
   

2. Set up a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Copy the .env.template file and rename it to .env:

```bash  
cp .env.template .env
```

4. Add your Groq API key to the .env file:

```
GROQ_API_KEY=<your-api-key>
```


## Usage

To run the ElevenEleven program, simply execute:

```bash
python main.py
```

or

```bash
python3 main.py
```

The program will initialize, and you can start conversing with the AI spiritual philosopher. Chat history will be saved automatically, and you can ask the AI to perform its current function—telling the current time in Central Standard Time (CST).

## Future Plans

- Add more advanced function-calling abilities.
- Expand the RAG method to improve information retrieval.
- Implement more comprehensive conversation features with varied philosophical insights.


## License

This project is licensed under the MIT License.




