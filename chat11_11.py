import sqlite3
from datetime import datetime
from typing import List, Dict, Any

import spacy
from groq import Groq
from groq import (
    GroqError, APIError, APIStatusError, APITimeoutError, APIConnectionError,
    APIResponseValidationError, BadRequestError, AuthenticationError,
    PermissionDeniedError, NotFoundError, ConflictError, UnprocessableEntityError,
    RateLimitError, InternalServerError
)
import numpy as np

from functions import get_date_time
from func_list import functions

from config import Config

cfg = Config()

# Load the SpaCy model for embeddings
nlp = spacy.load("en_core_web_md")  # Can switch to 'en_core_web_lg' for better results

try:
    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read()
except FileNotFoundError:
    system_prompt = "You are a helpful AI assistant."
except IOError as e:
    system_prompt = "You are a helpful AI assistant."

class Chat11_11:
    def __init__(self, api_key=cfg.groq_api_key, model=cfg.model, prompt_token_limit=cfg.prompt_token_limit, 
                 completion_token_limit=cfg.completion_token_limit, temperature=cfg.temperature, 
                 frequency_penalty=cfg.frequency_penalty, presence_penalty=cfg.presence_penalty):
        self.client = Groq(api_key=api_key)

        self.model = model
        self.prompt_token_limit = prompt_token_limit
        self.completion_token_limit = completion_token_limit
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.system_message = {"role": "system", "content": f"{system_prompt}"}
        self.chat_history = [self.system_message]
        
        self.db_connection = sqlite3.connect('chat_history.db')
        self.setup_database()

    def setup_database(self):
        cursor = self.db_connection.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         timestamp TEXT,
         role TEXT,
         content TEXT)
        ''')
        self.db_connection.commit()

    def save_message(self, role: str, content: str):
        cursor = self.db_connection.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute('INSERT INTO chat_history (timestamp, role, content) VALUES (?, ?, ?)',
                       (timestamp, role, content))
        self.db_connection.commit()

    def retrieve_relevant_history(self, query: str, limit: int = 5) -> List[str]:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT content FROM chat_history WHERE role IN ("user", "assistant") ORDER BY timestamp DESC LIMIT 1000')
        recent_messages = cursor.fetchall()

        if not recent_messages:
            return []

        messages = [msg[0] for msg in recent_messages]
        
        # Create embeddings for messages and the query using SpaCy
        query_vector = nlp(query).vector
        message_vectors = [nlp(message).vector for message in messages]

        # Calculate cosine similarities between the query and each message
        similarities = np.array([np.dot(query_vector, message_vector) /
                                (np.linalg.norm(query_vector) * np.linalg.norm(message_vector))
                                for message_vector in message_vectors])

        # Apply a recency factor
        recency_factor = np.linspace(0.5, 1, len(similarities))
        relevance_scores = similarities * recency_factor
        
        # Get the most relevant messages based on similarity and recency
        most_relevant_indices = relevance_scores.argsort()[-limit:][::-1]
        relevant_messages = [messages[i] for i in most_relevant_indices if relevance_scores[i] > 0]

        return relevant_messages

    def _manage_history(self, new_message: Dict[str, str]):
        self.chat_history.append(new_message)

        total_tokens = sum(len(msg["content"].split()) for msg in self.chat_history)

        while total_tokens > self.prompt_token_limit and len(self.chat_history) > 2:
            relevance_scores = self._calculate_relevance_scores(new_message["content"])
            least_relevant_index = min(range(1, len(self.chat_history) - 1),
                                       key=lambda i: relevance_scores[i-1])

            removed_msg = self.chat_history.pop(least_relevant_index)
            total_tokens -= len(removed_msg["content"].split())

    def _calculate_relevance_scores(self, query: str) -> np.ndarray:
        messages = [msg["content"] for msg in self.chat_history[1:]]
        
        # Create embeddings for chat history and query
        query_vector = nlp(query).vector
        message_vectors = [nlp(message).vector for message in messages]

        # Calculate cosine similarities
        similarities = np.array([np.dot(query_vector, message_vector) /
                                (np.linalg.norm(query_vector) * np.linalg.norm(message_vector))
                                for message_vector in message_vectors])

        recency_factor = np.linspace(0.5, 1, len(similarities))
        relevance_scores = similarities * recency_factor
        
        return relevance_scores

    def send_message(self, user_message: str) -> str:
        self.save_message("user", user_message)

        relevant_history = self.retrieve_relevant_history(user_message)
        context = "\n".join(relevant_history)

        self.chat_history = [self.system_message]
        if context:
            self.chat_history.append({"role": "system", "content": f"Relevant context from previous conversations:\n{context}"})

        self.chat_history.append({"role": "user", "content": user_message})
        self._manage_history({"role": "user", "content": user_message})

        try:
            chat_completion = self.client.chat.completions.create(
                messages=self.chat_history,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.completion_token_limit,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                functions=functions,
                function_call="auto"
            )

            response = chat_completion.choices[0].message

            if response.function_call:
                function_name = response.function_call.name
                if function_name == "get_date_time":
                    function_response = get_date_time()
                    self.chat_history.append({
                        "role": "function",
                        "name": function_name,
                        "content": function_response
                    })
                    
                    chat_completion = self.client.chat.completions.create(
                        messages=self.chat_history,
                        model=self.model,
                        temperature=self.temperature,
                        max_tokens=self.completion_token_limit,
                        frequency_penalty=self.frequency_penalty,
                        presence_penalty=self.presence_penalty,
                    )
                    response = chat_completion.choices[0].message.content
                else:
                    response = "I'm sorry, but I don't know how to call that function."
            else:
                response = response.content

        except APITimeoutError:
            return self.send_message(user_message)  # Retry the request
        except RateLimitError:
            return "I'm sorry, but I've reached my rate limit. Please try again in a moment."
        except (BadRequestError, UnprocessableEntityError):
            return "I'm sorry, but there was an error processing your request. Please try rephrasing your message."
        except (APIError, APIConnectionError, InternalServerError):
            return "I'm experiencing some technical difficulties. Please try again later."
        except GroqError:
            return "An unexpected error occurred. Please try again later."

        self.save_message("assistant", response)
        self._manage_history({"role": "assistant", "content": response})

        return response

    def __del__(self):
        if hasattr(self, 'db_connection'):
            self.db_connection.close()