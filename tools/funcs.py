import datetime
import pytz
import requests
from typing import Dict, Any, List, Optional


def get_date_time():
    """
    Returns the current date and time in Tennessee, USA.
    """
    tz = pytz.timezone('America/Chicago')  # Tennessee is in the Central Time Zone
    current_time = datetime.datetime.now(tz)
    return current_time.strftime("%Y-%m-%d %H:%M:%S %Z")


def query_wikidata(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Query Wikidata for information based on the given query string.

    Args:
    query (str): The search query or Wikidata entity ID (Q number).
    limit (int): Maximum number of results to return (default: 5).

    Returns:
    Dict[str, Any]: A dictionary containing the query results with the following structure:
        {
            "success": bool,
            "results": List[Dict[str, str]],
            "error": Optional[str]
        }

    The 'results' list contains dictionaries with 'id', 'label', and 'description' keys.

    Example usage:
    result = query_wikidata("Albert Einstein")
    result = query_wikidata("Q937")
    """
    endpoint_url = "https://www.wikidata.org/w/api.php"
    
    # Check if the query is a Wikidata ID (Q number)
    if query.startswith('Q') and query[1:].isdigit():
        params = {
            'action': 'wbgetentities',
            'ids': query,
            'format': 'json',
            'languages': 'en'
        }
    else:
        params = {
            'action': 'wbsearchentities',
            'search': query,
            'language': 'en',
            'format': 'json',
            'limit': limit
        }

    try:
        response = requests.get(endpoint_url, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        if 'search' in data:
            for item in data['search']:
                results.append({
                    'id': item['id'],
                    'label': item.get('label', ''),
                    'description': item.get('description', '')
                })
        elif 'entities' in data:
            entity = next(iter(data['entities'].values()))
            results.append({
                'id': entity['id'],
                'label': entity['labels'].get('en', {}).get('value', ''),
                'description': entity['descriptions'].get('en', {}).get('value', '')
            })

        return {
            "success": True,
            "results": results,
            "error": None
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "results": [],
            "error": f"Error querying Wikidata: {str(e)}"
        }
