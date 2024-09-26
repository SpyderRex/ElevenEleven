functions = [
    {
        "type": "function",
        "function": {
            "name": "get_date_time",
            "description": "Get the current date and time in Tennessee, USA",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_wikidata",
            "description": "Query Wikidata for information based on a given search term or Wikidata entity ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or Wikidata entity ID (Q number)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }
]
