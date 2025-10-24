import io
import random
import time
from contextlib import redirect_stdout
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover - Streamlit bundles pandas, but guard for safety
    pd = None

from app_components import (
    free_agent_rows,
    render_filterable_table,
    render_reserves_with_actions,
    render_table,
    roster_rows,
)
from constants import INIT_YEAR, TEAMS_INIT, RESERVES
from economy import next_season_base_budget, process_rewards_penalties
from injuries import assign_season_injuries, recover_injuries
from main import BOARD_FIRING_MESSAGES, apply_retirements, standings_table
from matchEngineSchedules import assign_dates, build_home_and_away, simulate_match
from models.team import Team
from organizeSquad import organize_squad
from retirement import season_end_retirements
from transfersAI import (
    ai_transfers,
    champion_poach_user,
    make_free_agent_pool,
    trim_ai_reserves,
)
from utils import season_dates

MAX_LOG_LINES = 500
TRANSFER_PREMIUM_RATE = 0.15


def set_flash(state: Dict[str, Any], level: str, message: str) -> None:
    state["flash"] = (level, message)


def display_flash(state: Dict[str, Any]) -> None:
    flash = state.get("flash")
    if not flash:
        return
    level, message = flash
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    else:
        st.info(message)
    state["flash"] = None


def rerun_app() -> None:
    """Request Streamlit to rerun the script, compatible across versions."""
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    elif hasattr(st, "rerun"):
        st.rerun()
    else:  # pragma: no cover - safeguard for unexpected Streamlit API changes
        raise RuntimeError("Streamlit rerun API is not available.")


def init_game_state() -> Dict[str, Any]:
    random.seed(time.time_ns())
    teams = [Team(meta) for meta in TEAMS_INIT]
    for team in teams:
        team.generate_initial_squad()
        team.top_up_youth(is_user=False)
        organize_squad(team)

    return {
        "teams": teams,
        "user_index": None,
        "year": INIT_YEAR,
        "prev_table": None,
        "season_dates": None,
        "schedule": [],
        "next_fixture_idx": 0,
        "season_active": False,
        "phase": "offseason",
        "transfer_window_closed": False,
        "history": [],
        "free_agents": [],
        "flash": None,
        "log": [
            "Welcome to MLSoccerMode Streamlit!",
            "Pick your club from the sidebar to begin your managerial career.",
        ],
    }


def append_log(state: Dict[str, Any], message: str) -> None:
    if not message:
        return
    for line in message.splitlines():
        text = line.strip()
        if text:
            state["log"].append(text)
    if len(state["log"]) > MAX_LOG_LINES:
        state["log"] = state["log"][-MAX_LOG_LINES:]


def capture_output(func, *args, **kwargs) -> Tuple[Any, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


def log_call(state: Dict[str, Any], func, *args, **kwargs):
    result, output = capture_output(func, *args, **kwargs)
    append_log(state, output)
    return result


def prepare_free_agent_pool(state: Dict[str, Any]) -> None:
    free_agents = make_free_agent_pool()
    if not free_agents:
        state["free_agents"] = []
        append_log(state, "No free agents generated for this window.")
        return

    reveal_count = max(1, len(free_agents) // 2)
    reveal_indices = set(random.sample(range(len(free_agents)), reveal_count))
    for idx, player in enumerate(free_agents):
        player.display_potential_range = idx in reveal_indices

    state["free_agents"] = free_agents
    append_log(state, f"Generated {len(free_agents)} free agents for this window.")


def sign_free_agent(state: Dict[str, Any], player_token: Optional[str]) -> None:
    if not player_token:
        set_flash(state, "warning", "Pick a free agent to sign.")
        return

    free_agents = state.get("free_agents", [])
    teams: List[Team] = state["teams"]
    user = teams[state["user_index"]]

    # Ensure squad is organized before checking reserve counts.
    organize_squad(user)

    target = None
    target_idx = None
    for idx, player in enumerate(free_agents):
        if str(id(player)) == player_token:
            target = player
            target_idx = idx
            break

    if target is None or target_idx is None:
        set_flash(state, "error", "Selected free agent is no longer available.")
        return

    if len(user.reserves) >= RESERVES:
        set_flash(
            state,
            "warning",
            f"{user.name} already has {len(user.reserves)} reserves. "
            f"Release or loan players before adding new signings.",
        )
        append_log(
            state,
            f"{user.name} blocked from signing {target.name}: reserves at capacity ({len(user.reserves)}/{RESERVES}).",
        )
        return

    price = target.value()
    if price > user.budget or not user.pay(price):
        set_flash(
            state,
            "error",
            f"Insufficient funds. {user.name} needs €{price:,}M but has €{user.budget:,}M.",
        )
        append_log(
            state,
            f"{user.name} failed to sign {target.name}: insufficient budget (€{price:,}M).",
        )
        return

    free_agents.pop(target_idx)
    user.reserves.append(target)
    organize_squad(user)

    message = (
        f"{user.name} signed {target.name} ({target.pos}, {target.rating} OVR, Age {target.age}) "
        f"for €{price:,}M. Remaining budget: €{user.budget:,}M."
    )
    append_log(state, message)
    set_flash(state, "success", message)


def poach_player(state: Dict[str, Any], token: Optional[str]) -> None:
    if not token:
        set_flash(state, "warning", "Select a poach target first.")
        return

    try:
        team_idx_str, player_id_str = token.split(":", 1)
        team_idx = int(team_idx_str)
    except ValueError:
        set_flash(state, "error", "Invalid selection.")
        return

    teams: List[Team] = state["teams"]
    user = teams[state["user_index"]]
    if team_idx < 0 or team_idx >= len(teams):
        set_flash(state, "error", "Chosen club was not found.")
        return
    seller = teams[team_idx]
    if seller is user:
        set_flash(state, "error", "Cannot poach from your own club.")
        return

    player = next((p for p in seller.all_players() if str(id(p)) == player_id_str), None)
    if player is None:
        set_flash(state, "error", "That player is no longer available.")
        return

    organize_squad(user)
    if len(user.reserves) >= RESERVES:
        set_flash(
            state,
            "warning",
            f"{user.name} already has {len(user.reserves)} reserves. "
            f"Release or loan players before adding new signings.",
        )
        append_log(
            state,
            f"{user.name} blocked from poaching {player.name}: reserves at capacity ({len(user.reserves)}/{RESERVES}).",
        )
        return

    base = player.value()
    premium = max(1, int(round(base * TRANSFER_PREMIUM_RATE)))
    total = base + premium

    if total > user.budget or not user.pay(total):
        set_flash(
            state,
            "error",
            f"Insufficient funds. {user.name} needs €{total:,}M but has €{user.budget:,}M.",
        )
        append_log(
            state,
            f"{user.name} could not poach {player.name} from {seller.name}: needs €{total:,}M.",
        )
        return

    seller.receive(total)
    for group in (seller.starters, seller.bench, seller.reserves):
        if player in group:
            group.remove(player)
            break

    user.reserves.append(player)
    organize_squad(user)
    organize_squad(seller)

    message = (
        f"{user.name} poached {player.name} ({player.pos}, {player.rating} OVR) from {seller.name} "
        f"for €{base:,}M + premium €{premium:,}M. "
        f"Remaining budget: €{user.budget:,}M. {seller.name} budget: €{seller.budget:,}M."
    )
    append_log(state, message)
    set_flash(state, "success", message)


def release_player(state: Dict[str, Any], token: Optional[str]) -> None:
    if not token:
        set_flash(state, "warning", "Choose a player to release.")
        return

    if ":" not in token:
        set_flash(state, "error", "Invalid release selection.")
        return

    group_key, player_id = token.split(":", 1)
    teams: List[Team] = state["teams"]
    user = teams[state["user_index"]]

    groups = {
        "Starters": user.starters,
        "Bench": user.bench,
        "Reserves": user.reserves,
    }
    pool = groups.get(group_key)
    if pool is None:
        set_flash(state, "error", "Unknown squad group.")
        return

    player = next((p for p in pool if str(id(p)) == player_id), None)
    if player is None:
        set_flash(state, "error", "Selected player is no longer in that group.")
        return

    fee = 1
    if fee > user.budget or not user.pay(fee):
        set_flash(state, "error", f"Not enough funds to pay the €{fee:,}M release fee.")
        append_log(
            state,
            f"{user.name} attempted to release {player.name} but lacked €{fee:,}M for the payout.",
        )
        return

    pool.remove(player)
    if hasattr(user, "unprotect_player"):
        user.unprotect_player(player)

    organize_squad(user)

    message = (
        f"{user.name} released {player.name} from {group_key}. "
        f"Budget after payout: €{user.budget:,}M."
    )
    append_log(state, message)
    set_flash(state, "success", message)


def finalize_transfer_window(state: Dict[str, Any]) -> None:
    if state.get("phase") != "preseason":
        set_flash(state, "warning", "Transfer window is not currently open.")
        return
    if state.get("transfer_window_closed"):
        set_flash(state, "info", "Transfer window already closed.")
        return

    teams: List[Team] = state["teams"]
    user = teams[state["user_index"]]
    if len(user.reserves) > RESERVES:
        set_flash(
            state,
            "warning",
            f"Reduce reserves to {RESERVES} or fewer before finalizing the window.",
        )
        append_log(
            state,
            f"Finalize blocked: {user.name} has {len(user.reserves)} reserves (limit {RESERVES}).",
        )
        return
    free_agents = state.get("free_agents", [])

    append_log(state, "Finalizing transfer window...")

    if state["prev_table"]:
        log_call(
            state,
            champion_poach_user,
            state["prev_table"],
            user,
            0.70,
            0.20,
            TRANSFER_PREMIUM_RATE,
            0.90,
        )

    other_teams = [club for club in teams if club is not user]
    random.shuffle(other_teams)
    for club in other_teams:
        log_call(state, ai_transfers, club, free_agents)
        organize_squad(club)
        log_call(state, trim_ai_reserves, club)

    state["free_agents"] = free_agents

    log_call(state, apply_retirements, teams)

    tm_open, tm_close, season_start, season_end = state["season_dates"]

    append_log(state, "Assigning season injuries...")
    for club in teams:
        log_call(
            state,
            assign_season_injuries,
            club,
            season_start,
            season_end,
            club is user,
        )
    append_log(state, "Injuries assigned.")

    for club in teams:
        organize_squad(club)

    fixtures = build_home_and_away(teams)
    try:
        schedule = assign_dates(fixtures, season_start, season_end)
    except RuntimeError as exc:
        set_flash(state, "error", str(exc))
        append_log(state, f"Failed to build schedule: {exc}")
        return

    state["schedule"] = schedule
    state["next_fixture_idx"] = 0
    state["season_active"] = True
    state["phase"] = "season"
    state["transfer_window_closed"] = True
    state["free_agents"] = []

    append_log(
        state,
        f"Season schedule created with {len(schedule)} fixtures.",
    )
    set_flash(state, "success", "Transfer window closed. Season ready to begin.")


def start_new_season(state: Dict[str, Any]) -> None:
    if state["user_index"] is None:
        append_log(state, "Select a team before starting a season.")
        return
    if state["season_active"]:
        append_log(state, "Season already underway. Finish it before starting another.")
        return
    if state.get("phase") == "preseason" and not state.get("transfer_window_closed"):
        set_flash(state, "info", "Transfer window already open. Manage it from the Transfers tab.")
        return

    year = state["year"]
    tm_open, tm_close, _, season_start, season_end = season_dates(year)
    state["season_dates"] = (tm_open, tm_close, season_start, season_end)
    state["season_active"] = False
    state["phase"] = "preseason"
    state["transfer_window_closed"] = False
    state["schedule"] = []
    state["next_fixture_idx"] = 0
    state["free_agents"] = []

    append_log(state, f"================  Season {year}-{year + 1}  ================")

    teams: List[Team] = state["teams"]
    user = teams[state["user_index"]]

    for club in teams:
        club.reset_season_stats()
        club.top_up_youth(is_user=(club is user))
        organize_squad(club)

    prepare_free_agent_pool(state)
    append_log(
        state,
        f"Transfer window open {tm_open.isoformat()} → {tm_close.isoformat()}. "
        "Use the Transfers tab to sign, poach, or release players before continuing.",
    )
    set_flash(state, "info", "Transfer window is open. Manage your moves in the Transfers tab.")


def current_fixture(state: Dict[str, Any]) -> Optional[Tuple[date, Team, Team, str]]:
    if not state["season_active"]:
        return None
    idx = state["next_fixture_idx"]
    if idx >= len(state["schedule"]):
        return None
    when, matchup = state["schedule"][idx]
    team_a, team_b, venue = matchup
    return when, team_a, team_b, venue


def play_next_match(state: Dict[str, Any]) -> None:
    if not state["season_active"]:
        append_log(state, "No active season. Start a new one from the sidebar.")
        return

    idx = state["next_fixture_idx"]
    if idx >= len(state["schedule"]):
        append_log(state, "Season complete. Start a new campaign to continue.")
        finish_season(state)
        return

    when, (team_a, team_b, venue) = state["schedule"][idx]
    user = state["teams"][state["user_index"]]

    log_call(state, recover_injuries, team_a, when, team_a is user)
    log_call(state, recover_injuries, team_b, when, team_b is user)

    organize_squad(team_a, on=when)
    organize_squad(team_b, on=when)

    goals_a, goals_b = simulate_match(team_a, team_b, venue, when)

    if venue == "homeA":
        score_line = f"{when.isoformat()} · {team_a.name} {goals_a}-{goals_b} {team_b.name}"
    elif venue == "homeB":
        score_line = f"{when.isoformat()} · {team_b.name} {goals_b}-{goals_a} {team_a.name}"
    else:
        score_line = f"{when.isoformat()} · {team_a.name} {goals_a}-{goals_b} {team_b.name} (neutral site)"

    append_log(state, score_line)

    state["next_fixture_idx"] += 1

    if state["next_fixture_idx"] >= len(state["schedule"]):
        finish_season(state)


def simulate_remaining_season(state: Dict[str, Any]) -> None:
    while state["season_active"] and state["next_fixture_idx"] < len(state["schedule"]):
        play_next_match(state)


def finish_season(state: Dict[str, Any]) -> None:
    if not state["season_active"]:
        return

    teams: List[Team] = state["teams"]
    table = standings_table(teams)
    season_label = f"{state['year']}-{state['year'] + 1}"

    append_log(state, "=== FINAL TABLE ===")
    table_snapshot: List[Dict[str, Any]] = []

    for pos, club in enumerate(table, start=1):
        gd = club.gf - club.ga
        append_log(
            state,
            f"{pos:>2}. {club.name:<18} {club.points:>3} pts  GF {club.gf:>3}  GA {club.ga:>3}  GD {gd:+}",
        )
        table_snapshot.append(
            {
                "Pos": pos,
                "Team": club.name,
                "Pts": club.points,
                "GF": club.gf,
                "GA": club.ga,
                "GD": gd,
                "Avg": club.avg_rating(),
                "Budget": club.budget,
            }
        )

    log_call(state, process_rewards_penalties, table)
    log_call(state, season_end_retirements, teams)

    for club in teams:
        for player in club.all_players():
            player.season_progression()

    append_log(state, "=== NEXT SEASON BASE BUDGETS (APPLIED) ===")
    for club in teams:
        base = next_season_base_budget(club)
        club.budget = base
        append_log(state, f"{club.name:<18} -> Base Budget: €{club.budget:,}M")

    user_team = teams[state["user_index"]]
    user_pos = next(
        (idx for idx, club in enumerate(table, start=1) if club is user_team),
        None,
    )

    forced_switch = False
    if user_pos and user_pos > user_team.objective:
        if random.random() < 0.13:
            forced_switch = True

    if forced_switch:
        firing_message = random.choice(BOARD_FIRING_MESSAGES).format(team=user_team.name)
        append_log(state, firing_message)
        bottom_candidates = [club for club in table[-2:] if club is not user_team]
        if bottom_candidates:
            new_team = bottom_candidates[0]
            state["user_index"] = teams.index(new_team)
            append_log(state, f"You are now managing {new_team.name}.")
            user_team = new_team
        else:
            append_log(state, "No replacement club available; you remain in place.")
    else:
        append_log(state, f"The board keeps faith with you at {user_team.name}.")

    state["history"].append(
        {
            "season": season_label,
            "table": table_snapshot,
            "managed_team": user_team.name,
        }
    )

    state["prev_table"] = table[:]
    state["schedule"] = []
    state["next_fixture_idx"] = 0
    state["season_active"] = False
    state["phase"] = "offseason"
    state["transfer_window_closed"] = True
    state["free_agents"] = []
    state["year"] += 1




def render_overview(state: Dict[str, Any]) -> None:
    teams: List[Team] = state["teams"]
    managed = teams[state["user_index"]] if state["user_index"] is not None else None

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Season", f"{state['year']}-{state['year'] + 1}")
        if managed:
            st.metric("Club", managed.name)
    with col2:
        if managed:
            st.metric("Budget", f"€{managed.budget:,}M")
            st.metric("Objective", f"Finish ≤ {managed.objective}")

    fixture = current_fixture(state)
    if fixture:
        when, team_a, team_b, venue = fixture
        venue_note = {
            "homeA": f"{team_a.name} home",
            "homeB": f"{team_b.name} home",
        }.get(venue, "neutral venue")
        st.info(
            f"Next fixture: {when.isoformat()} · {team_a.name} vs {team_b.name} ({venue_note})"
        )
    elif state["season_active"]:
        st.info("All fixtures complete for the current season.")
    elif state.get("phase") == "preseason" and state.get("season_dates"):
        tm_open, tm_close, _, _ = state["season_dates"]
        st.info(
            f"Transfer window open {tm_open.isoformat()} → {tm_close.isoformat()}. "
            "Head to the Transfers tab when you are ready to make moves."
        )

    if teams:
        table = standings_table(teams)
        records = []
        for pos, club in enumerate(table, start=1):
            records.append(
                {
                    "Pos": pos,
                    "Team": club.name,
                    "Pts": club.points,
                    "GF": club.gf,
                    "GA": club.ga,
                    "GD": club.gf - club.ga,
                    "Avg": club.avg_rating(),
                    "Budget": club.budget,
                    "Managed": "You" if club is managed else "",
                }
            )
        st.subheader("Standings Snapshot")
        render_table(records)


def render_transfers(state: Dict[str, Any]) -> None:
    if state["user_index"] is None:
        st.info("Select a club to manage transfers.")
        return

    if state.get("phase") != "preseason":
        st.info("Transfer window closed. Start a new season from the sidebar to reopen it.")
        return

    teams: List[Team] = state["teams"]
    user = teams[state["user_index"]]
    organize_squad(user)
    tm_open, tm_close, _, _ = state["season_dates"]
    reserves_full = len(user.reserves) >= RESERVES

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Budget", f"€{user.budget:,}M")
    with col2:
        st.metric("Reserves", f"{len(user.reserves)}/{RESERVES}")
    with col3:
        st.metric("Window", f"{tm_open.isoformat()} → {tm_close.isoformat()}")

    if reserves_full:
        if len(user.reserves) > RESERVES:
            st.warning(f"Reserves exceed the limit. Release players to reach {RESERVES}.")
        else:
            st.warning(
                f"Reserves are at capacity ({RESERVES}). Release players before signing or poaching new ones."
            )

    st.markdown("### Free Agents")
    free_agents = state.get("free_agents", [])
    if free_agents:
        agent_lookup = {str(id(player)): player for player in free_agents}

        def render_free_agent_results(filtered_df) -> None:
            display_df = filtered_df.drop(columns=["Token"], errors="ignore")
            if display_df.empty:
                st.info("No free agents match your filters.")
                return

            widths = [1.1, 3.2, 1.0, 1.6, 0.9, 0.9, 1.6, 1.4]
            headers = ["Action", "Name", "Pos", "Nation", "Age", "OVR", "Potential Range", "Value (€M)"]
            header_cols = st.columns(widths)
            for col, title in zip(header_cols, headers):
                col.markdown(f"**{title}**")

            def safe_int(value: Any) -> Any:
                if value in ("", None):
                    return ""
                try:
                    if pd.isna(value):
                        return ""
                except TypeError:
                    pass
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return value

            for _, row in filtered_df.iterrows():
                token = row.get("Token")
                player = agent_lookup.get(token)
                cols = st.columns(widths)

                help_text = None
                disabled = False
                if reserves_full:
                    help_text = "Free up reserve slots before signing."
                    disabled = True
                if player is None:
                    disabled = True

                with cols[0]:
                    if st.button(
                        "Sign",
                        key=f"sign_free_agent_{token}",
                        disabled=disabled,
                        help=help_text,
                        use_container_width=True,
                    ):
                        sign_free_agent(state, token)
                        rerun_app()

                with cols[1]:
                    st.markdown(f"**{row.get('Name', '')}**")
                with cols[2]:
                    st.write(row.get("Pos", ""))
                with cols[3]:
                    st.write(row.get("Nation", ""))
                with cols[4]:
                    st.write(safe_int(row.get("Age", "")))
                with cols[5]:
                    st.write(safe_int(row.get("OVR", "")))
                with cols[6]:
                    potential_range = row.get("Potential Range", "")
                    try:
                        if pd.isna(potential_range):
                            potential_range = ""
                    except TypeError:
                        pass
                    st.write(potential_range)
                with cols[7]:
                    value = row.get("Value (€M)", "")
                    if value in ("", None):
                        st.write("")
                    else:
                        try:
                            if pd.isna(value):  # type: ignore[arg-type]
                                st.write("")
                            else:
                                st.write(f"€{int(value):,}M")
                        except (ValueError, TypeError):
                            st.write(value)

        render_filterable_table(
            free_agent_rows(free_agents),
            "free_agents",
            "Free Agents",
            on_render=render_free_agent_results,
            exclude_columns=["Token"],
        )
    else:
        st.info("No free agents remain in the pool.")

    st.markdown("### Poach From Other Clubs")
    poach_targets = []
    for idx, club in enumerate(teams):
        if club is user:
            continue
        for group_name, group in (("Starters", club.starters), ("Bench", club.bench), ("Reserves", club.reserves)):
            for player in group:
                base = player.value()
                premium = max(1, int(round(base * TRANSFER_PREMIUM_RATE)))
                total = base + premium
                if total > user.budget:
                    continue
                poach_targets.append(
                    {
                        "Token": f"{idx}:{id(player)}",
                        "Club": club.name,
                        "Group": group_name,
                        "Name": player.name,
                        "Pos": player.pos,
                        "OVR": player.rating,
                        "Age": player.age,
                        "Total (€M)": total,
                        "Base (€M)": base,
                        "Premium (€M)": premium,
                    }
                )

    if poach_targets:
        def render_poach_results(filtered_df) -> None:
            display_df = filtered_df.drop(columns=["Token"], errors="ignore")
            if display_df.empty:
                st.info("No poach targets match your filters.")
                return

            widths = [1.1, 2.6, 1.0, 1.8, 1.0, 0.9, 1.6, 1.6, 1.6]
            headers = [
                "Action",
                "Name",
                "Pos",
                "Club",
                "Group",
                "OVR",
                "Age",
                "Total (€M)",
                "Premium (€M)",
            ]
            header_cols = st.columns(widths)
            for col, title in zip(header_cols, headers):
                col.markdown(f"**{title}**")

            def safe_int(value: Any) -> Any:
                if value in ("", None):
                    return ""
                try:
                    if pd.isna(value):
                        return ""
                except TypeError:
                    pass
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return value

            for _, row in filtered_df.iterrows():
                token = row.get("Token")
                cols = st.columns(widths)

                help_text = None
                disabled = False
                if reserves_full:
                    help_text = "Free up reserve slots before poaching."
                    disabled = True

                with cols[0]:
                    if st.button(
                        "Poach",
                        key=f"poach_target_{token}",
                        disabled=disabled,
                        help=help_text,
                        use_container_width=True,
                    ):
                        poach_player(state, token)
                        rerun_app()

                with cols[1]:
                    st.markdown(f"**{row.get('Name', '')}**")
                with cols[2]:
                    st.write(row.get("Pos", ""))
                with cols[3]:
                    st.write(row.get("Club", ""))
                with cols[4]:
                    st.write(row.get("Group", ""))
                with cols[5]:
                    st.write(safe_int(row.get("OVR", "")))
                with cols[6]:
                    st.write(safe_int(row.get("Age", "")))
                with cols[7]:
                    total_val = row.get("Total (€M)", "")
                    if total_val in ("", None):
                        st.write("")
                    else:
                        try:
                            if pd.isna(total_val):  # type: ignore[arg-type]
                                st.write("")
                            else:
                                st.write(f"€{int(total_val):,}M")
                        except (ValueError, TypeError):
                            st.write(total_val)
                with cols[8]:
                    premium_val = row.get("Premium (€M)", "")
                    if premium_val in ("", None):
                        st.write("")
                    else:
                        try:
                            if pd.isna(premium_val):  # type: ignore[arg-type]
                                st.write("")
                            else:
                                st.write(f"€{int(premium_val):,}M")
                        except (ValueError, TypeError):
                            st.write(premium_val)

        render_filterable_table(
            poach_targets,
            "poach_targets",
            "Poach Targets",
            on_render=render_poach_results,
            exclude_columns=["Token"],
        )
    else:
        st.info("No affordable poach targets available with the current budget.")

    st.markdown("---")
    if st.button("Finalize Transfer Window & Begin Season"):
        finalize_transfer_window(state)
        rerun_app()


def render_squad(state: Dict[str, Any]) -> None:
    if state["user_index"] is None:
        st.info("Select a club to view its squad.")
        return

    team: Team = state["teams"][state["user_index"]]
    st.subheader(f"{team.name} Squad Overview")
    st.markdown(f"**Formation:** {team.formation}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Starters**")
        render_table(roster_rows(team.starters))
    with col2:
        st.markdown("**Bench**")
        render_table(roster_rows(team.bench))

    st.markdown("")
    render_reserves_with_actions(state, team, release_player, rerun_app)


def render_history(state: Dict[str, Any]) -> None:
    if not state["history"]:
        st.info("Complete at least one season to populate history.")
        return

    for entry in reversed(state["history"]):
        with st.expander(f"Season {entry['season']} · Managed {entry['managed_team']}", expanded=False):
            render_table(entry["table"])


def render_log(state: Dict[str, Any]) -> None:
    log_text = "\n".join(state["log"])
    st.text_area("Activity Log", log_text, height=420, disabled=True)


def run_app() -> None:
    st.set_page_config(page_title="MLSoccerMode", layout="wide")

    if "game_state" not in st.session_state:
        st.session_state["game_state"] = init_game_state()

    state = st.session_state["game_state"]

    with st.sidebar:
        st.header("Career Controls")

        if st.button("Reset Career"):
            st.session_state["game_state"] = init_game_state()
            rerun_app()

        if state["user_index"] is None:
            team_names = [team["name"] for team in TEAMS_INIT]
            selected = st.selectbox("Choose your team", team_names)
            if st.button("Start Career"):
                idx = team_names.index(selected)
                state["user_index"] = idx
                append_log(state, f"You now manage {selected}.")
                rerun_app()
        else:
            team: Team = state["teams"][state["user_index"]]
            st.metric("Club", team.name)
            st.metric("Budget", f"€{team.budget:,}M")
            st.metric("Objective", f"Finish ≤ {team.objective}")

            phase = state.get("phase")
            if state["season_active"]:
                matches_left = len(state["schedule"]) - state["next_fixture_idx"]
                st.metric("Matches Remaining", matches_left)
                if st.button("Play Next Match"):
                    play_next_match(state)
                    rerun_app()
                if st.button("Simulate Season"):
                    with st.spinner("Simulating season..."):
                        simulate_remaining_season(state)
                    rerun_app()
            elif phase == "preseason" and not state.get("transfer_window_closed"):
                tm_open, tm_close, _, _ = state["season_dates"]
                st.info(
                    f"Transfer window open until {tm_close.isoformat()}. "
                    "Use the Transfers tab to manage your squad."
                )
                if st.button("Finalize Transfer Window"):
                    finalize_transfer_window(state)
                    rerun_app()
            else:
                if st.button("Start New Season"):
                    start_new_season(state)
                    rerun_app()

    st.title("MLSoccerMode · Streamlit Edition")
    display_flash(state)
    tabs = st.tabs(["Overview", "Transfers", "Squad", "History", "Log"])

    with tabs[0]:
        render_overview(state)
    with tabs[1]:
        render_transfers(state)
    with tabs[2]:
        render_squad(state)
    with tabs[3]:
        render_history(state)
    with tabs[4]:
        render_log(state)


if __name__ == "__main__":
    run_app()
