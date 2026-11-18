import asyncio
import json

import pytest

from factory_investigator.investigation import investigate
from factory_investigator.simulation import generate
from factory_investigator.twin import Twin


def test_langgraph_matches_local():
    pytest.importorskip('langgraph.graph')
    rows = generate()
    scores = Twin.fit(rows[:360], rows[360:504]).score(rows[504:])
    assert investigate(scores, 'langgraph') == investigate(scores, 'local')


def test_mcp_registered_tools_and_invocation():
    pytest.importorskip('mcp')
    from factory_investigator.gateway import create_server
    async def check():
        server = create_server()
        registered = await server.list_tools()
        assert {t.name for t in registered} == {'search_maintenance', 'investigate_demo'}
        result = await server.call_tool('search_maintenance', {'query': 'bearing'})
        # SDK versions may return content alone or (content, structured_content).
        content = result[0] if isinstance(result, tuple) else result
        text = ' '.join(item.text for item in content if hasattr(item, 'text'))
        assert 'synthetic-pump-manual' in text
    asyncio.run(check())
