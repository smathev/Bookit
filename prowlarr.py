from dotenv import load_dotenv
import os
import requests
from urllib.parse import quote

# Load environment variables from .env file
load_dotenv()

# Access the variables using os.getenv
api_key = os.getenv('API_KEY')
base_url = os.getenv('BASE_URL')
search_endpoint = os.getenv('SEARCH_ENDPOINT')
test_search_movie = os.getenv('TEST_SEARCH_MOVIE')
test_search_tv = os.getenv('TEST_SEARCH_TV')
indexer_endpoint= os.getenv('INDEXER_ENDPOINT')

# Set up headers with API key
headers = {
    'X-Api-Key': api_key
}

def _old_test_scenarios():
    movie_test = base_url + search_endpoint + test_search_movie
    tv_test = base_url + search_endpoint + test_search_tv


    def test_movie():
        # Make a GET request with headers and disable SSL verification
        response_movie = requests.get(movie_test, headers=headers, verify=False)
        return response_movie

    def test_tv():
        response_tv = requests.get(tv_test, headers=headers, verify=False)
        return response_tv


def _search_for_book(search_term, indexers=None):
    if not search_term:
        raise ValueError("search_term is required")
    encoded_term = quote(search_term)        
    if indexers:
        indexer_params = '&'.join(f'indexerIds={i}' for i in indexers)
        search_query = f"query={encoded_term}&{indexer_params}&categories=7000&type=search"
    else:
        search_query = f"query={encoded_term}&indexerIds=-2&categories=7000&type=search"
    
    book_search = base_url + search_endpoint + search_query
    print(f"Debug - request URL: {book_search}")  # Debug print
    response_book = requests.get(book_search, headers=headers, verify=False)       
    return response_book

def _indexer_list():
    indexer_list = base_url + indexer_endpoint
    response_indexer = requests.get(indexer_list, headers=headers, verify=False)
    return response_indexer

def _get_indexer_name_and_id():
    indexer_list = _indexer_list()
    indexer_json = indexer_list.json()
    indexer_dict = {}
    for indexer in indexer_json:
        indexer_dict[indexer['name']] = indexer['id']
    return indexer_dict

indexers = [4]

test_function = _search_for_book(search_term="Lord of the Rings", indexers=indexers)
json_book = test_function.json()

print (json_book)

# Print the JSON objects
#print(json_tv)
#print(json_movie)