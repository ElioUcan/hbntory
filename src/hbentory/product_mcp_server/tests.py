import asyncio
import os

from fastmcp import Client

MCP_URL = os.getenv("PRODUCT_MCP_URL", "http://127.0.0.1:8100/mcp")


async def run_manual_checks() -> None:
    async with Client(MCP_URL) as client:
        print("Tools:", [t.name for t in await client.list_tools()])

        res_list = await client.call_tool("list_products", {"limit": 5})
        print("list_products count:", res_list.data.count)

        res_search = await client.call_tool("list_products", {"query": "keyboard"})
        print("search 'keyboard' results:", len(res_search.data.results))

        res_sku = await client.call_tool(
            "get_product_details", {"product_identifier": "HB-LAP-1001"}
        )
        print("detail by SKU:", res_sku.data.name)

        res_id = await client.call_tool("get_product_details", {"product_identifier": "1"})
        print("detail by ID:", res_id.data.sku)

        res_404 = await client.call_tool(
            "get_product_details",
            {"product_identifier": "NON-EXISTENT-999"},
            raise_on_error=False,
        )
        print("not found error:", res_404.is_error, res_404.content)

        res_bad = await client.call_tool(
            "get_product_details",
            {"product_identifier": "bad/id"},
            raise_on_error=False,
        )
        print("invalid id error:", res_bad.is_error, res_bad.content)


if __name__ == "__main__":
    asyncio.run(run_manual_checks())
