"""Local stdio MCP gateway. No SQL execution or equipment-control tools."""
from .investigation import investigate
from .retrieval import Retriever
from .simulation import generate
from .twin import Twin


def create_server():
    from mcp.server.fastmcp import FastMCP
    server = FastMCP("factory-investigator")

    @server.tool()
    def search_maintenance(query: str, limit: int = 3) -> list[dict]:
        """Retrieve synthetic demo maintenance passages with citations."""
        return Retriever().search(query, limit)

    @server.tool()
    def investigate_demo(seed: int = 42) -> dict:
        """Investigate a synthetic pump fault; does not read or modify real equipment."""
        rows = generate(seed)
        twin = Twin.fit(rows[:360], rows[360:504])
        return investigate(twin.score(rows[504:]))

    return server


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
