import json
from typing import List, Dict, Any

from groq import Groq
from groq import (
    GroqError, APIError, APIStatusError, APITimeoutError, APIConnectionError,
    APIResponseValidationError, BadRequestError, AuthenticationError,
    PermissionDeniedError, NotFoundError, ConflictError, UnprocessableEntityError,
    RateLimitError, InternalServerError
)

from tools.funcs import get_date_time, query_wikidata
from tools.func_list import functions
from config import Config
from memory.memory import Memory

cfg = Config()

try:
    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read()
except (FileNotFoundError, IOError):
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
        self.system_message = {"role": "system", "content": system_prompt}
        self.memory = Memory()
        self.available_functions = {
            "get_date_time": get_date_time,
            "query_wikidata": query_wikidata,
        }

    def send_message(self, user_message: str) -> str:
        self.memory.save_message("user", user_message)
        context = self.memory.get_context(user_message, self.prompt_token_limit)
        messages = [self.system_message] + context + [{"role": "user", "content": user_message}]

        try:
            final_response = self._process_conversation(messages)
        except APITimeoutError:
            return self.send_message(user_message)  # Retry the request
        except RateLimitError:
            return "I'm sorry, but I've reached my rate limit. Please try again in a moment."
        except (BadRequestError, UnprocessableEntityError) as e:
            return f"I'm sorry, but there was an error processing your request: {e}"
        except (APIError, APIConnectionError, InternalServerError):
            return "I'm experiencing some technical difficulties. Please try again later."
        except GroqError:
            return "An unexpected error occurred. Please try again later."

        self.memory.save_message("assistant", final_response)
        return final_response

    def _process_conversation(self, messages: List[Dict[str, Any]]) -> str:
        while True:
            response = self._get_completion(messages)
            
            if not response.tool_calls:
                return response.content

            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})

            for tool_call in response.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                function_to_call = self.available_functions.get(function_name)
                if function_to_call:
                    function_response = function_to_call(**function_args)
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
                else:
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": f"Unknown function '{function_name}'"})
                    })

    def _get_completion(self, messages: List[Dict[str, Any]]) -> Any:
        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.completion_token_limit,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            tools=functions,
            tool_choice="auto"
        )
        return chat_completion.choices[0].message

    def __del__(self):
        if hasattr(self, 'memory'):
            del self.memory
