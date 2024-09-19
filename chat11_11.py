import sqlite3
from datetime import datetime
from typing import List, Dict, Any
import json

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
nlp = spacy.load("en_core_web_md")  # Using the large model for better embeddings

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
        self.short_term_memory = [self.system_message]
        
        self.db_connection = sqlite3.connect('chat_history.db')
        self.setup_database()

    def setup_database(self):
        cursor = self.db_connection.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         timestamp TEXT,
         role TEXT,
         content TEXT,
         embedding BLOB)
        ''')
        self.db_connection.commit()

    def save_message(self, role: str, content: str):
        cursor = self.db_connection.cursor()
        timestamp = datetime.now().isoformat()
        embedding = nlp(content).vector.tobytes()
        cursor.execute('INSERT INTO chat_history (timestamp, role, content, embedding) VALUES (?, ?, ?, ?)',
                       (timestamp, role, content, embedding))
        self.db_connection.commit()

    def retrieve_relevant_history(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT role, content, embedding FROM chat_history ORDER BY timestamp DESC LIMIT 1000')
        recent_messages = cursor.fetchall()

        if not recent_messages:
            return []

        query_vector = nlp(query).vector
        
        similarities = []
        for role, content, embedding in recent_messages:
            message_vector = np.frombuffer(embedding, dtype=np.float32)
            similarity = np.dot(query_vector, message_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(message_vector))
            similarities.append((similarity, role, content))

        similarities.sort(reverse=True)
        return [{"role": role, "content": content} for _, role, content in similarities[:limit]]

    def _manage_short_term_memory(self, new_message: Dict[str, str]):
        self.short_term_memory.append(new_message)

        total_tokens = sum(len(msg["content"].split()) for msg in self.short_term_memory)

        while total_tokens > self.prompt_token_limit and len(self.short_term_memory) > 2:
            removed_msg = self.short_term_memory.pop(1)  # Remove the oldest non-system message
            total_tokens -= len(removed_msg["content"].split())

    def send_message(self, user_message: str) -> str:
        self.save_message("user", user_message)

        relevant_history = self.retrieve_relevant_history(user_message)
        
        context_messages = [
            {"role": "system", "content": "Here's some relevant context from previous conversations:"}
        ] + relevant_history

        messages = self.short_term_memory + context_messages + [{"role": "user", "content": user_message}]

        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
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
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": function_response
                    })
                    
                    chat_completion = self.client.chat.completions.create(
                        messages=messages,
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
        self._manage_short_term_memory({"role": "user", "content": user_message})
        self._manage_short_term_memory({"role": "assistant", "content": response})

        return response

    def __del__(self):
        if hasattr(self, 'db_connection'):
            self.db_connection.close()
