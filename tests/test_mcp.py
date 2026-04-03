"""MCP server integration tests using FastMCP in-memory client."""

from __future__ import annotations

import json

import pytest
from fastmcp import Client

from diatagma.mcp.server import create_mcp_server
from diatagma.mcp import tools as mcp_tools
from tests.conftest import seed_spec_file


@pytest.fixture
def populated_specs(tmp_specs_dir, sample_prefixes, sample_templates):
    """Create a .specs/ dir with config and sample specs for MCP tests."""
    config_dir = tmp_specs_dir / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        "statuses: [pending, in-progress, review, done, cancelled]\n"
        "types: [feature, bug, epic, spike]\n"
        "auto_complete_parent: true\n",
        encoding="utf-8",
    )
    (config_dir / "prefixes.yaml").write_text(
        'TST:\n  description: "Test project"\n  template: story\n',
        encoding="utf-8",
    )
    templates_dir = config_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    (templates_dir / "story.md").write_text(
        "## Description\n\n## Behavior\n", encoding="utf-8"
    )

    seed_spec_file(
        tmp_specs_dir, "TST-001", "First spec", business_value=500, story_points=5
    )
    seed_spec_file(
        tmp_specs_dir, "TST-002", "Second spec", business_value=300, story_points=3
    )
    seed_spec_file(
        tmp_specs_dir,
        "TST-003",
        "Blocked spec",
        business_value=100,
        story_points=2,
        links={"blocked_by": ["TST-001"]},
    )
    (tmp_specs_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
    return tmp_specs_dir


@pytest.fixture
def mcp_server(populated_specs):
    """Create a FastMCP server pointed at populated_specs."""
    mcp_tools._warmed_caches.clear()
    return create_mcp_server(populated_specs)


@pytest.fixture
async def mcp_client(mcp_server):
    """Async client connected to the in-memory MCP server."""
    async with Client(mcp_server) as client:
        yield client


# ---------------------------------------------------------------------------
# Tools — get_spec
# ---------------------------------------------------------------------------


class TestGetSpec:
    async def test_returns_full_spec(self, mcp_client):
        result = await mcp_client.call_tool("get_spec", {"spec_id": "TST-001"})
        data = json.loads(result.content[0].text)
        assert data["meta"]["id"] == "TST-001"
        assert data["meta"]["title"] == "First spec"
        assert "body" in data

    async def test_not_found(self, mcp_client):
        result = await mcp_client.call_tool(
            "get_spec", {"spec_id": "TST-999"}, raise_on_error=False
        )
        assert result.is_error


# ---------------------------------------------------------------------------
# Tools — list_specs
# ---------------------------------------------------------------------------


class TestListSpecs:
    async def test_list_all(self, mcp_client):
        result = await mcp_client.call_tool("list_specs", {})
        data = json.loads(result.content[0].text)
        assert data["total"] == 3
        assert len(data["specs"]) == 3

    async def test_filter_by_status(self, mcp_client):
        result = await mcp_client.call_tool("list_specs", {"status": "pending"})
        data = json.loads(result.content[0].text)
        assert data["total"] == 3  # all pending

    async def test_pagination(self, mcp_client):
        result = await mcp_client.call_tool("list_specs", {"limit": 2})
        data = json.loads(result.content[0].text)
        assert len(data["specs"]) == 2
        assert data["next_cursor"] is not None

        # Fetch next page
        result2 = await mcp_client.call_tool(
            "list_specs", {"limit": 2, "cursor": data["next_cursor"]}
        )
        data2 = json.loads(result2.content[0].text)
        assert len(data2["specs"]) == 1
        assert data2["next_cursor"] is None


# ---------------------------------------------------------------------------
# Tools — get_ready_specs
# ---------------------------------------------------------------------------


class TestGetReadySpecs:
    async def test_returns_unblocked(self, mcp_client):
        result = await mcp_client.call_tool("get_ready_specs", {})
        data = json.loads(result.content[0].text)
        ids = [s["id"] for s in data]
        assert "TST-001" in ids
        assert "TST-002" in ids
        # TST-003 is blocked by TST-001
        assert "TST-003" not in ids

    async def test_limit(self, mcp_client):
        result = await mcp_client.call_tool("get_ready_specs", {"limit": 1})
        data = json.loads(result.content[0].text)
        assert len(data) == 1


# ---------------------------------------------------------------------------
# Tools — create_spec
# ---------------------------------------------------------------------------


class TestCreateSpec:
    async def test_create(self, mcp_client):
        result = await mcp_client.call_tool(
            "create_spec", {"title": "New feature", "prefix": "TST"}
        )
        data = json.loads(result.content[0].text)
        assert data["meta"]["id"] == "TST-004"
        assert data["meta"]["title"] == "New feature"

    async def test_create_default_prefix(self, mcp_client):
        result = await mcp_client.call_tool("create_spec", {"title": "Auto prefix"})
        data = json.loads(result.content[0].text)
        assert data["meta"]["id"].startswith("TST-")


# ---------------------------------------------------------------------------
# Tools — update_spec
# ---------------------------------------------------------------------------


class TestUpdateSpec:
    async def test_update_title(self, mcp_client):
        result = await mcp_client.call_tool(
            "update_spec", {"spec_id": "TST-001", "title": "Updated title"}
        )
        data = json.loads(result.content[0].text)
        assert data["meta"]["title"] == "Updated title"

    async def test_update_no_fields_errors(self, mcp_client):
        result = await mcp_client.call_tool(
            "update_spec", {"spec_id": "TST-001"}, raise_on_error=False
        )
        assert result.is_error


# ---------------------------------------------------------------------------
# Tools — claim_spec / release_spec
# ---------------------------------------------------------------------------


class TestClaimRelease:
    async def test_claim(self, mcp_client):
        result = await mcp_client.call_tool(
            "claim_spec", {"spec_id": "TST-001", "agent_id": "test-agent"}
        )
        data = json.loads(result.content[0].text)
        assert data["meta"]["assignee"] == "test-agent"
        assert data["meta"]["status"] == "in-progress"

    async def test_claim_already_claimed(self, mcp_client):
        await mcp_client.call_tool(
            "claim_spec", {"spec_id": "TST-001", "agent_id": "agent-a"}
        )
        result = await mcp_client.call_tool(
            "claim_spec",
            {"spec_id": "TST-001", "agent_id": "agent-b"},
            raise_on_error=False,
        )
        assert result.is_error

    async def test_claim_same_agent_ok(self, mcp_client):
        await mcp_client.call_tool(
            "claim_spec", {"spec_id": "TST-001", "agent_id": "agent-a"}
        )
        result = await mcp_client.call_tool(
            "claim_spec", {"spec_id": "TST-001", "agent_id": "agent-a"}
        )
        assert not result.is_error

    async def test_release(self, mcp_client):
        await mcp_client.call_tool(
            "claim_spec", {"spec_id": "TST-001", "agent_id": "test-agent"}
        )
        result = await mcp_client.call_tool(
            "release_spec", {"spec_id": "TST-001", "agent_id": "test-agent"}
        )
        data = json.loads(result.content[0].text)
        assert data["meta"]["assignee"] == ""
        assert data["meta"]["status"] == "pending"

    async def test_release_wrong_agent(self, mcp_client):
        await mcp_client.call_tool(
            "claim_spec", {"spec_id": "TST-001", "agent_id": "agent-a"}
        )
        result = await mcp_client.call_tool(
            "release_spec",
            {"spec_id": "TST-001", "agent_id": "agent-b"},
            raise_on_error=False,
        )
        assert result.is_error


# ---------------------------------------------------------------------------
# Tools — search_specs
# ---------------------------------------------------------------------------


class TestSearchSpecs:
    async def test_search_title(self, mcp_client):
        result = await mcp_client.call_tool("search_specs", {"query": "First"})
        data = json.loads(result.content[0].text)
        assert len(data) == 1
        assert data[0]["id"] == "TST-001"

    async def test_search_no_results(self, mcp_client):
        result = await mcp_client.call_tool("search_specs", {"query": "nonexistent"})
        # Empty list returns no content blocks
        if result.content:
            data = json.loads(result.content[0].text)
            assert len(data) == 0
        else:
            pass  # empty content = empty results


# ---------------------------------------------------------------------------
# Tools — validate_specs
# ---------------------------------------------------------------------------


class TestValidateSpecs:
    async def test_validate(self, mcp_client):
        result = await mcp_client.call_tool("validate_specs", {})
        data = json.loads(result.content[0].text)
        assert "issues" in data
        assert "dependency_cycles" in data
        assert "total_issues" in data


# ---------------------------------------------------------------------------
# Tools — get_dependency_graph
# ---------------------------------------------------------------------------


class TestGetDependencyGraph:
    async def test_graph(self, mcp_client):
        result = await mcp_client.call_tool("get_dependency_graph", {})
        data = json.loads(result.content[0].text)
        assert "nodes" in data
        assert "edges" in data
        node_ids = [n["id"] for n in data["nodes"]]
        assert "TST-001" in node_ids


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


class TestResources:
    async def test_spec_resource(self, mcp_client):
        contents = await mcp_client.read_resource("spec://TST-001")
        text = contents[0].text
        assert "TST-001" in text
        assert "First spec" in text

    async def test_settings_resource(self, mcp_client):
        contents = await mcp_client.read_resource("config://settings")
        data = json.loads(contents[0].text)
        assert "statuses" in data

    async def test_statuses_resource(self, mcp_client):
        contents = await mcp_client.read_resource("config://statuses")
        data = json.loads(contents[0].text)
        assert "pending" in data["statuses"]

    async def test_templates_resource(self, mcp_client):
        contents = await mcp_client.read_resource("config://templates")
        data = json.loads(contents[0].text)
        assert "story" in data["templates"]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


class TestPrompts:
    async def test_create_story(self, mcp_client):
        result = await mcp_client.get_prompt("create_story", {"title": "New feature"})
        text = result.messages[0].content.text
        assert "New feature" in text
        assert "create_spec" in text

    async def test_run_spike(self, mcp_client):
        result = await mcp_client.get_prompt("run_spike", {"topic": "MCP research"})
        text = result.messages[0].content.text
        assert "MCP research" in text
        assert "spike" in text

    async def test_triage_backlog(self, mcp_client):
        result = await mcp_client.get_prompt("triage_backlog", {})
        text = result.messages[0].content.text
        assert "pending" in text
        assert "validate_specs" in text


# ---------------------------------------------------------------------------
# Statelessness
# ---------------------------------------------------------------------------


class TestStatelessness:
    async def test_external_mutation_reflected(self, mcp_client, populated_specs):
        """Modifying a spec file externally should be reflected on next tool call."""
        # Read original
        result = await mcp_client.call_tool("get_spec", {"spec_id": "TST-001"})
        data = json.loads(result.content[0].text)
        assert data["meta"]["title"] == "First spec"

        # Mutate the file externally
        spec_file = next(populated_specs.glob("TST-001-*.md"))
        content = spec_file.read_text(encoding="utf-8")
        content = content.replace("First spec", "Externally modified")
        spec_file.write_text(content, encoding="utf-8")

        # Next call should reflect the change
        result2 = await mcp_client.call_tool("get_spec", {"spec_id": "TST-001"})
        data2 = json.loads(result2.content[0].text)
        assert data2["meta"]["title"] == "Externally modified"
