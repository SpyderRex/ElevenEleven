import os
import sqlite3
from datetime import datetime
from typing import List, Dict
import numpy as np
import spacy

memory_dir = os.path.dirname(os.path.abspath(__file__))

# Load the SpaCy model for embeddings
nlp = spacy.load("en_core_web_md")

class Memory:
    def __init__(self, db_path=os.path.join(memory_dir, 'chat_history.db')):
        self.db_connection = sqlite3.connect(db_path)
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
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         role TEXT,
         content TEXT)
        ''')
        self.db_connection.commit()

    def save_message(self, role: str, content: str):
        cursor = self.db_connection.cursor()
        timestamp = datetime.now().isoformat()
        embedding = nlp(content).vector.tobytes()
        
        # Save to long-term memory (chat_history)
        cursor.execute('INSERT INTO chat_history (timestamp, role, content, embedding) VALUES (?, ?, ?, ?)',
                       (timestamp, role, content, embedding))
        
        # Save to short-term memory
        cursor.execute('INSERT INTO short_term_memory (role, content) VALUES (?, ?)', (role, content))
        
        self.db_connection.commit()

    def get_context(self, query: str, token_limit: int) -> List[Dict[str, str]]:
        short_term = self._get_short_term_memory(token_limit)
        
        if not short_term:
            return self._get_long_term_memory(query, token_limit)
        
        short_term_tokens = sum(len(msg['content'].split()) for msg in short_term)
        remaining_tokens = max(0, token_limit - short_term_tokens)
        
        if remaining_tokens > 0:
            long_term = self._get_long_term_memory(query, remaining_tokens)
            return long_term + short_term
        
        return short_term

    def _get_short_term_memory(self, token_limit: int) -> List[Dict[str, str]]:
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT role, content FROM short_term_memory ORDER BY id DESC')
        messages = []
        total_tokens = 0
        
        for role, content in cursor.fetchall():
            message_tokens = len(content.split())
            if total_tokens + message_tokens > token_limit:
                break
            messages.insert(0, {"role": role, "content": content})
            total_tokens += message_tokens
        
        return messages

    def _get_long_term_memory(self, query: str, token_limit: int) -> List[Dict[str, str]]:
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
        
        relevant_messages = []
        total_tokens = 0
        for _, role, content in similarities:
            message_tokens = len(content.split())
            if total_tokens + message_tokens > token_limit:
                break
            relevant_messages.append({"role": role, "content": content})
            total_tokens += message_tokens

        return relevant_messages

    def trim_short_term_memory(self, max_entries: int = 50):
        cursor = self.db_connection.cursor()
        cursor.execute('DELETE FROM short_term_memory WHERE id NOT IN (SELECT id FROM short_term_memory ORDER BY id DESC LIMIT ?)', (max_enties,))
        self.db_connection.commit()

    def __del__(self):
        if hasattr(self, 'db_connection'):
            self.db_connection.close()
