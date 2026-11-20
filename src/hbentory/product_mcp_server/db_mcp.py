from toolbox_core import ToolboxClient
import asyncio

# update the url to point to your server
async def main():
    async with ToolboxClient("http://127.0.0.1:5000") as client:
        # these tools can be passed to your application!
        tools = await client.load_toolset("toolset_name")

if __name__ == '__main__':
    asyncio.run(main())
