import os
from typing import Annotated, Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field, ValidationError

from hbentory.product_mcp_server.schemas import ProductDetail, ProductListOutput

load_dotenv()

DEFAULT_PRODUCT_API_URL = "http://127.0.0.1:5001"
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 8100

mcp = FastMCP(
    name="HBentory Product Catalog",
    instructions=(
        "Read-only bridge to the external HBentory Product API. "
        "Use these tools exclusively for product catalog metadata; "
        "branch inventory quantities live in the local database."
    ),
)


def _get_api_base_url() -> str:
    return (os.getenv("PRODUCT_API_URL") or DEFAULT_PRODUCT_API_URL).rstrip("/")


def _get_timeout_seconds() -> float:
    raw = os.getenv("PRODUCT_API_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return max(0.5, float(raw))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("message") or payload.get("error") or response.reason)
    except ValueError:
        pass
    return response.reason or "Unknown upstream error"


def _fetch_json(
    path: str,
    *,
    params: dict[str, str | int] | None = None,
    not_found_message: str | None = None,
) -> dict[str, Any]:
    """Query the external Product API and raise ToolError with context on failure."""
    base_url = _get_api_base_url()
    timeout = _get_timeout_seconds()
    url = f"{base_url}{path}"

    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.Timeout as exc:
        raise ToolError(
            f"Product API request timed out after {timeout:.1f}s while requesting '{path}'."
        ) from exc
    except requests.ConnectionError as exc:
        raise ToolError(
            f"Cannot connect to Product API at {base_url}. "
            "Verify that the external Product API service is running."
        ) from exc
    except requests.RequestException as exc:
        raise ToolError(f"Product API communication error: {exc}") from exc

    if response.status_code == 404:
        raise ToolError(not_found_message or f"Product resource not found ({path}).")
    if response.status_code == 400:
        raise ToolError(f"Invalid Product API request: {_extract_error_message(response)}")
    if response.status_code >= 500:
        raise ToolError(
            f"Product API unavailable (HTTP {response.status_code}): "
            f"{_extract_error_message(response)}"
        )
    if response.status_code != 200:
        raise ToolError(
            f"Unexpected Product API status HTTP {response.status_code}: "
            f"{_extract_error_message(response)}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ToolError("Product API returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise ToolError("Product API returned an unexpected payload type.")
    return data


@mcp.tool
def list_products(
    query: Annotated[
        str | None,
        Field(description="Optional search text matched against name, SKU, description, or tags."),
    ] = None,
    category: Annotated[
        str | None,
        Field(description="Optional exact category filter (for example 'Laptops')."),
    ] = None,
    limit: Annotated[
        int,
        Field(ge=1, le=100, description="Maximum number of products to return (1-100)."),
    ] = 20,
    offset: Annotated[
        int,
        Field(ge=0, description="Pagination offset into the matching results."),
    ] = 0,
) -> ProductListOutput:
    """List available catalog products from the external Product API."""
    params: dict[str, str | int] = {"limit": limit, "offset": offset}
    if query and query.strip():
        params["q"] = query.strip()
    if category and category.strip():
        params["category"] = category.strip()

    data = _fetch_json("/api/v1/products", params=params)
    try:
        return ProductListOutput.model_validate(data)
    except ValidationError as exc:
        raise ToolError(f"Invalid product list format from Product API: {exc}") from exc


@mcp.tool
def get_product_details(
    product_identifier: Annotated[
        str,
        Field(
            min_length=1,
            max_length=60,
            description="Numeric product ID (e.g. '1') or SKU (e.g. 'HB-LAP-1001').",
        ),
    ],
) -> ProductDetail:
    """Retrieve catalog details for a single product by numeric ID or SKU."""
    identifier = product_identifier.strip()
    if not identifier or any(char in identifier for char in "/?#"):
        raise ToolError(
            "Invalid product_identifier: provide a non-empty numeric ID or SKU without '/', '?', or '#'."
        )

    encoded = quote(identifier, safe="")
    data = _fetch_json(
        f"/api/v1/products/{encoded}",
        not_found_message=f"Product '{identifier}' was not found in the external catalog.",
    )
    try:
        return ProductDetail.model_validate(data)
    except ValidationError as exc:
        raise ToolError(
            f"Invalid product detail format for '{identifier}': {exc}"
        ) from exc


def main() -> None:
    transport = os.getenv("PRODUCT_MCP_TRANSPORT", "streamable-http")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        host = os.getenv("PRODUCT_MCP_HOST", DEFAULT_MCP_HOST)
        port = int(os.getenv("PRODUCT_MCP_PORT", str(DEFAULT_MCP_PORT)))
        mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
