import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from on_knowledge.storage import Store


@pytest.mark.asyncio
async def test_real_stdio_handshake_and_notebook_scope(tmp_path):
    store = Store(tmp_path)
    allowed = store.create_notebook("Allowed")
    store.create_notebook("Hidden")
    store.save_note(allowed["id"], "My note", "A local knowledge layer")
    run = Path(__file__).resolve().parents[1] / "apps/api/run.py"
    parameters = StdioServerParameters(command=os.environ.get("OPENNOTEBOOK_MCP_EXE", sys.executable), args=([] if os.environ.get("OPENNOTEBOOK_MCP_EXE") else [str(run)]) + ["--mcp", "--data-dir", str(tmp_path), "--notebook", allowed["id"]], env={**os.environ, "PYTHONUTF8": "1"})
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert {"search_sources", "read_source", "search_notes", "get_chunk"} <= names
            assert not any(name.startswith(("delete", "create", "update")) for name in names)
            notebooks = await session.call_tool("list_notebooks", {})
            text = str(notebooks.content)
            assert "Allowed" in text and "Hidden" not in text
            notes = await session.call_tool("search_notes", {"query": "knowledge"})
            assert "My note" in str(notes.content)
            missing = await session.call_tool("get_chunk", {"chunk_id": "foreign"})
            assert missing.isError
