import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import streamlit as st

from config.settings import DB_PATH, WAREHOUSE_WIDTH, WAREHOUSE_HEIGHT
from simulation.warehouse import build_default_warehouse
from storage.db import Database

st.set_page_config(page_title="AI Warehouse Dashboard", layout="wide")

db = Database(DB_PATH)
warehouse = build_default_warehouse()

ZONE_COLORS = {
    "STORAGE": "#4A90D9",
    "PICKUP": "#5CB85C",
    "PACKAGING": "#F0AD4E",
    "DISPATCH": "#D9534F",
    "CHARGING": "#F7E967",
}


def draw_warehouse(latest_positions):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(0, WAREHOUSE_WIDTH)
    ax.set_ylim(0, WAREHOUSE_HEIGHT)
    ax.invert_yaxis()
    ax.set_xticks(range(0, WAREHOUSE_WIDTH + 1, 1))
    ax.set_yticks(range(0, WAREHOUSE_HEIGHT + 1, 1))
    ax.grid(True, linewidth=0.3, color="lightgray")

    for zone in warehouse.zones.values():
        rect = patches.Rectangle(
            (zone.x, zone.y), zone.width, zone.height,
            facecolor=ZONE_COLORS.get(zone.zone_type.value, "gray"),
            alpha=0.4, edgecolor="black",
        )
        ax.add_patch(rect)
        ax.text(zone.x + 0.2, zone.y + 0.5, zone.name, fontsize=8, fontweight="bold")

    for entry in latest_positions:
        ax.plot(entry["x"] + 0.5, entry["y"] + 0.5, "o", markersize=16, color="purple")
        ax.text(entry["x"] + 0.5, entry["y"] + 0.9, entry["robot_id"], fontsize=9, ha="center")
    ax.set_title("Warehouse — Live View")
    return fig


st.title("🏭 AI Warehouse Control — Live Dashboard")

latest = db.get_latest_telemetry_per_robot()

col1, col2 = st.columns([2, 1])

with col1:
    if latest:
        st.pyplot(draw_warehouse(latest))
    else:
        st.info("Abhi tak koi telemetry nahi mili — MCP server chal raha hai kya check karo.")

with col2:
    st.subheader("Robot Status")
    for row in latest:
        st.metric(label=f"{row['robot_id']} — {row['state']}", value=f"{row['battery']:.1f}% battery")

st.subheader("Recent AI Actions (Audit Log)")
audit_rows = db.get_audit_log(limit=10)
st.table([
    {
        "Time": a["recorded_at"],
        "Tool": a["tool_name"],
        "Approved": "Yes" if a["approved"] else "No",
        "Reason": a["reason"] or "-",
    }
    for a in audit_rows
])

st.caption(f"Auto-refreshing every 2 seconds — last refresh {time.strftime('%H:%M:%S')}")
time.sleep(2)
st.rerun()