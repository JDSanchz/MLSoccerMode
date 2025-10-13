# === Add these imports at top ===
import csv, os
from datetime import datetime
import random
from prompts import prompt_int
from playerCost import est_cost_eur

# === Add this helper (million-euro labeler + reward logic) ===
def collect_price_labels(user, n=3, csv_path="price_labels.csv", year=None):
    """
    Ask the user to label realistic prices for n random players.
    Stores rows: timestamp, team, year, rating, age, model_value, user_price.
    Outcome: 80% +€7M, 13% +€10M, 7% +3 potential to user's lowest-potential player.
    """
    # Prepare CSV (write header if file doesn't exist)
    new_file = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp", "team", "year", "rating", "age", "model_value_M", "user_price_M"])

        print("\nHelp improve the price model! Please give realistic market prices.\n"
              "Consider real-world + FIFA/FC valuations.\n")

        for i in range(1, n + 1):
            rating = random.randint(64, 95)
            age = random.randint(16, 39)

            # Current model estimate (in millions) using your model function
            model_val_M = est_cost_eur(age, rating)  # assumed to return "millions" like your budgets

            print(f"\nPlayer #{i}")
            print(f"  Rating: {rating}   Age: {age}")
            print(f"  Model estimate: €{model_val_M:,}M")

            user_price = prompt_int("Your price (1–250M): ", 1, 250)

            writer.writerow([
                datetime.utcnow().isoformat(timespec="seconds"),
                getattr(user, "name", "UserTeam"),
                year if year is not None else "",
                rating,
                age,
                model_val_M,
                user_price
            ])

        # === Reward / perk ===
        roll = random.random()
        if roll < 0.80:
            user.receive(7)
            print(f"\n🎁 Thanks! {user.name} receives €7M.")
        elif roll < 0.93:
            user.receive(10)
            print(f"\n🎁 Jackpot! {user.name} receives €10M.")
        else:
            # +5 to lowest-potential player (capped 95) and reveal range
            squad = list(user.all_players())
            if squad:
                low = min(squad, key=lambda p: getattr(p, "potential", p.rating))
                old_range = low.potential_range
                low.apply_potential_boost(5)
                print(
                    f"\n✨ Development boost! {low.name}'s potential range is now revealed and improved: "
                    f"{old_range} → {low.potential_range}"
                )

