from fastmcp import FastMCP
from requests import get

mcp = FastMCP('List products mcp')

@mcp.tool
def list_products():
    url = 'http://localhost:5000'
    request = get(url)
    return request
