from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.toolbox_toolset import ToolboxToolset
from dotenv import load_dotenv
import os

load_dotenv()

mcp_url = os.getenv("MCP_URL")
toolbox_url = os.getenv("TOOLBOX_URL")

SYS_PROMPT = """
Usar las herramientas de productos para obtener product_id y metadatos del catálogo.
Usar las herramientas de stock/sucursales para consultar cantidades y ubicaciones usando product_id o branch_id.
Nunca inventar IDs ni cantidades si una herramienta no devuelve datos.
"""

stock_toolset = ToolboxToolset(
    server_url=str(mcp_url),
    toolset_name = 'mi-toolset-stock'
)

root_agent = Agent(
    model = 'gemini-3.6-flash',
    name="main_Agent",
    instruction = SYS_PROMPT,
    tools=[stock_toolset, McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=str(toolbox_url)
        )

    )]
)
