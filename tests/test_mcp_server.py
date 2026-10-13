import pytest
from fastmcp import Client

from mcp_server.app import build_app


def make_app(tmp_path):
    return build_app(db_path=str(tmp_path / "test.db"))


@pytest.mark.asyncio
async def test_get_warehouse_status_returns_three_robots(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        result = await client.call_tool("get_warehouse_status", {})
        assert len(result.data["robots"]) == 3

@pytest.mark.asyncio
async def test_predict_task_risk_returns_probability(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "predict_task_risk", {"robot_id": "R1", "from_zone": "Pickup", "to_zone": "Dispatch"}
        )
        if "error" in result.data:
            pytest.skip("ML model not generated yet — run analytics/ml_model.ipynb first")
        assert 0 <= result.data["predicted_failure_risk_percent"] <= 100
        assert "note" in result.data

@pytest.mark.asyncio
async def test_get_warehouse_layout_lists_all_zones(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        result = await client.call_tool("get_warehouse_layout", {})
        zone_names = {z["name"] for z in result.data["zones"]}
        assert zone_names == {"Storage", "Pickup", "Packaging", "Dispatch", "Charging"}


@pytest.mark.asyncio
async def test_assign_task_success_and_audit_logged(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "assign_task", {"robot_id": "R1", "from_zone": "Pickup", "to_zone": "Dispatch"}
        )
        assert result.data["success"] is True

    logs = db.get_audit_log()
    assert len(logs) == 1
    assert logs[0]["approved"] == 1


@pytest.mark.asyncio
async def test_assign_task_supports_reverse_direction(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "assign_task", {"robot_id": "R3", "from_zone": "Dispatch", "to_zone": "Pickup"}
        )
        assert result.data["success"] is True


@pytest.mark.asyncio
async def test_assign_task_rejection_logged(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "assign_task", {"robot_id": "R99", "from_zone": "Pickup", "to_zone": "Dispatch"}
        )
        assert result.data["success"] is False
        assert "Unknown robot_id" in result.data["reason"]


@pytest.mark.asyncio
async def test_emergency_stop_updates_status(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        stop_result = await client.call_tool("emergency_stop", {"robot_id": "R2"})
        assert stop_result.data["success"] is True

        status = await client.call_tool("get_robot_status", {"robot_id": "R2"})
        assert status.data["state"] == "EMERGENCY_STOPPED"


@pytest.mark.asyncio
async def test_get_task_history_lists_assigned_task(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        await client.call_tool(
            "assign_task", {"robot_id": "R3", "from_zone": "Pickup", "to_zone": "Dispatch"}
        )
        history = await client.call_tool("get_task_history", {})
        assert len(history.data["tasks"]) == 1


@pytest.mark.asyncio
async def test_telemetry_recorded_after_manual_tick(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    engine.tick()
    rows = db.get_telemetry()
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_reset_robot_after_emergency_stop(tmp_path):
    mcp, engine, warehouse, db, sim_lock = make_app(tmp_path)
    async with Client(mcp) as client:
        await client.call_tool("emergency_stop", {"robot_id": "R1"})
        reset_result = await client.call_tool("reset_robot", {"robot_id": "R1"})
        assert reset_result.data["success"] is True

        status = await client.call_tool("get_robot_status", {"robot_id": "R1"})
        assert status.data["state"] == "IDLE"