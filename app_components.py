from __future__ import annotations

import html
from typing import Any, Callable, Dict, Iterable, List, Optional

import streamlit as st

try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover - Streamlit bundles pandas, but guard for safety
    pd = None

from typing import TYPE_CHECKING

from constants import FORMATIONS

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from models.team import Team

FORMATION_LAYOUTS: Dict[str, Dict[str, List[tuple[float, float]]]] = {
    "4-3-3": {
        "GK": [(50, 92)],
        "CB": [(32, 74), (68, 74)],
        "LB": [(15, 68)],
        "RB": [(85, 68)],
        "CM": [(30, 50), (50, 42), (70, 50)],
        "LW": [(20, 26)],
        "RW": [(80, 26)],
        "ST": [(50, 16)],
    },
    "4-4-2": {
        "GK": [(50, 92)],
        "CB": [(32, 74), (68, 74)],
        "LB": [(15, 68)],
        "RB": [(85, 68)],
        "CDM": [(40, 52)],
        "CAM": [(60, 44)],
        "LW": [(22, 32)],
        "RW": [(78, 32)],
        "ST": [(44, 18), (56, 18)],
    },
    "3-5-2": {
        "GK": [(50, 92)],
        "CB": [(28, 74), (50, 74), (72, 74)],
        "CDM": [(38, 56), (62, 56)],
        "CAM": [(50, 42)],
        "LW": [(22, 36)],
        "RW": [(78, 36)],
        "ST": [(44, 20), (56, 20)],
    },
}

PITCH_CSS = """
<style>
.pitch-wrapper {
    position: relative;
    width: 100%;
    max-width: 640px;
    margin: 0 auto 1.2rem auto;
}
.pitch-surface {
    position: relative;
    width: 100%;
    padding-top: 150%;
    border-radius: 16px;
    background: linear-gradient(135deg, #0b6b29 0%, #13813d 100%);
    box-shadow: inset 0 0 0 3px rgba(255,255,255,0.4), 0 12px 32px rgba(0,0,0,0.25);
    overflow: hidden;
}
.pitch-surface::before,
.pitch-surface::after {
    content: "";
    position: absolute;
    left: 5%;
    right: 5%;
    border: 2px solid rgba(255,255,255,0.45);
    border-radius: 8px;
}
.pitch-surface::before {
    top: 8%;
    bottom: 8%;
}
.pitch-surface::after {
    top: 24%;
    bottom: 24%;
    border-left: none;
    border-right: none;
}
.pitch-player {
    position: absolute;
    transform: translate(-50%, -50%);
    min-width: 120px;
    max-width: 160px;
    padding: 6px 10px;
    border-radius: 12px;
    background: rgba(12,12,12,0.68);
    color: #f2f2f2;
    text-align: center;
    font-size: 0.85rem;
    line-height: 1.25;
    border: 1px solid rgba(255,255,255,0.35);
}
.pitch-player__name {
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.pitch-player__meta {
    font-size: 0.78rem;
    opacity: 0.8;
}
@media (max-width: 768px) {
    .pitch-player {
        min-width: 90px;
        font-size: 0.75rem;
    }
}
</style>
"""

_PITCH_CSS_INJECTED = False


def inject_pitch_css() -> None:
    global _PITCH_CSS_INJECTED
    if _PITCH_CSS_INJECTED:
        return
    st.markdown(PITCH_CSS, unsafe_allow_html=True)
    _PITCH_CSS_INJECTED = True


def roster_rows(players) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for player in players:
        injury = (
            player.injured_until.isoformat()
            if getattr(player, "injured_until", None)
            else "Fit"
        )
        revealed = getattr(player, "display_potential_range", False)
        potential_range = (
            getattr(player, "potential_range", "")
            if revealed
            else "Hidden"
        )
        rows.append(
            {
                "Name": player.name,
                "Pos": player.pos,
                "Nation": player.nation,
                "Age": player.age,
                "OVR": player.rating,
                "Range": potential_range,
                "Status": injury,
            }
        )
    return rows


def free_agent_rows(players) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for player in players:
        potential_range = (
            getattr(player, "potential_range", "")
            if getattr(player, "display_potential_range", False)
            else "Hidden"
        )
        rows.append(
            {
                "Token": str(id(player)),
                "Name": player.name,
                "Pos": player.pos,
                "Nation": player.nation,
                "Age": player.age,
                "OVR": player.rating,
                "Potential Range": potential_range,
                "Value (€M)": player.value(),
            }
        )
    return rows


def render_table(records: List[Dict[str, Any]]) -> None:
    if pd is not None:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)
    else:  # pragma: no cover - fallback for unexpected pandas absence
        st.table(records)


def render_filterable_table(
    records: List[Dict[str, Any]],
    table_id: str,
    title: str,
    pos_field: str = "Pos",
    rating_field: str = "OVR",
    on_render: Optional[Callable[[Any], None]] = None,
    exclude_columns: Optional[Iterable[str]] = None,
) -> None:
    if not records:
        st.info(f"No {title.lower()} available.")
        return

    if pd is None:  # pragma: no cover - fallback when pandas unavailable
        st.table(records)
        return

    df = pd.DataFrame(records)
    working = df.copy()
    exclude_set = set(exclude_columns or [])

    if pos_field in working.columns:
        positions = sorted(
            {pos for pos in working[pos_field].dropna().unique() if isinstance(pos, str)}
        )
        if positions:
            selected_positions = st.multiselect(
                f"{title} positions",
                positions,
                default=positions,
                key=f"{table_id}_pos_filter",
            )
            if selected_positions:
                working = working[working[pos_field].isin(selected_positions)]
            else:
                working = working.iloc[0:0]

    if rating_field in working.columns:
        working[rating_field] = pd.to_numeric(
            working[rating_field], errors="coerce"
        )
        rating_series = working[rating_field].dropna()
        if not rating_series.empty:
            min_rating = int(rating_series.min())
            max_rating = int(rating_series.max())
            if min_rating != max_rating:
                min_selected, max_selected = st.slider(
                    f"{title} rating range",
                    min_rating,
                    max_rating,
                    (min_rating, max_rating),
                    key=f"{table_id}_rating_filter",
                )
                working = working[
                    (working[rating_field] >= min_selected)
                    & (working[rating_field] <= max_selected)
                ]
            else:
                st.caption(f"{title} rating fixed at {min_rating}.")
        else:
            working = working.iloc[0:0]

    if working.empty:
        st.info(f"No {title.lower()} match your filters.")
        return

    columns = [col for col in working.columns if col not in exclude_set]
    if not columns:
        columns = list(working.columns)

    default_sort_index = (
        columns.index(rating_field) if rating_field in columns else 0
    )
    sort_column = st.selectbox(
        f"{title} sort column",
        columns,
        index=default_sort_index,
        key=f"{table_id}_sort_column",
    )
    sort_order = st.radio(
        f"{title} sort order",
        ["Descending", "Ascending"],
        horizontal=True,
        index=0,
        key=f"{table_id}_sort_order",
    )

    working = working.sort_values(
        by=sort_column,
        ascending=(sort_order == "Ascending"),
        kind="mergesort",
    )

    filtered = working.reset_index(drop=True)

    if on_render:
        on_render(filtered)
        return

    display_df = filtered.drop(columns=exclude_set, errors="ignore")
    st.dataframe(display_df, use_container_width=True)


def formation_slots(formation: str) -> List[str]:
    config = FORMATIONS.get(formation, {})
    slots: List[str] = []
    for pos, count in config.items():
        slots.extend([pos] * count)
    return slots


def render_reserves_with_actions(
    state: Dict[str, Any],
    team: "Team",
    on_release: Callable[[Dict[str, Any], str], None],
    rerun_callback: Callable[[], None],
) -> None:
    st.markdown("**Reserves**")
    reserves = list(team.reserves)
    if not reserves:
        st.info("No reserve players at the moment.")
        return

    widths = [1.1, 3.2, 1.0, 1.6, 0.9, 0.9, 1.6, 1.8]
    headers = ["Action", "Name", "Pos", "Nation", "Age", "OVR", "Range", "Status"]
    header_cols = st.columns(widths)
    for col, title in zip(header_cols, headers):
        col.markdown(f"**{title}**")

    def safe_int(value: Any) -> Any:
        if value in ("", None):
            return ""
        try:
            if pd is not None and pd.isna(value):
                return ""
        except TypeError:
            pass
        try:
            return int(value)
        except (ValueError, TypeError):
            return value

    for player in reserves:
        token = f"Reserves:{id(player)}"
        potential_range = (
            getattr(player, "potential_range", "")
            if getattr(player, "display_potential_range", False)
            else "Hidden"
        )
        injury = (
            player.injured_until.isoformat()
            if getattr(player, "injured_until", None)
            else "Fit"
        )

        cols = st.columns(widths)
        with cols[0]:
            if st.button(
                "Release",
                key=f"release_reserve_{token}",
                help="Release player for €1M fee.",
                use_container_width=True,
            ):
                on_release(state, token)
                rerun_callback()
        with cols[1]:
            st.markdown(f"**{player.name}**")
        with cols[2]:
            st.write(player.pos)
        with cols[3]:
            st.write(player.nation)
        with cols[4]:
            st.write(safe_int(player.age))
        with cols[5]:
            st.write(safe_int(player.rating))
        with cols[6]:
            st.write(potential_range)
        with cols[7]:
            st.write(injury)
