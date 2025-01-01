from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API credentials from environment
api_url = os.getenv('HARDCOVER_API_URL')
api_key = os.getenv('HARDCOVER_API_KEY')

# Set up the transport with the API key
transport = RequestsHTTPTransport(
    url=api_url,
    headers={'Authorization': api_key}
)

# Create the client
client = Client(transport=transport, fetch_schema_from_transport=True)

def search_books(title, author=None):
    # Define two different queries - one with author filter, one without
    query_with_author = gql("""
    query SearchBooks($title: String!, $author: String!) {
        books(
            order_by: {users_read_count: desc}
            where: {
                title: {_ilike: $title},
                contributions: {author: {name: {_ilike: $author}}}
            }
            limit: 10
        ) {
            users_read_count
            title
            contributions {
                author {
                    name
                    id
                }
            }
            image {
                url
            }
        }
    }
    """)

    query_without_author = gql("""
    query SearchBooks($title: String!) {
        books(
            order_by: {users_read_count: desc}
            where: {
                title: {_ilike: $title}
            }
            limit: 10
        ) {
            users_read_count
            title
            contributions {
                author {
                    name
                    id
                }
            }
            image {
                url
            }
        }
    }
    """)
    
    # Choose query and prepare variables based on whether author is provided
    if author:
        query = query_with_author
        variables = {
            "title": f"%{title}%",
            "author": f"%{author}%"
        }
    else:
        query = query_without_author
        variables = {
            "title": f"%{title}%"
        }
    
    # Execute the query with variables
    result = client.execute(query, variable_values=variables)
    return result

result = search_books("I'm just saying")
print(result)