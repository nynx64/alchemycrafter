import tkinter as tk
from tkinter import ttk
import json
import re
import os
import sys

#load reagents json
def get_resource_path(relative_path):
    """Get the absolute path to a resource."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
reagents_file = get_resource_path("reagents.json")
with open(reagents_file, "r") as file:
    reagents = json.load(file)["reagents"]

def parse_dice(dice_str):
    """Parse dice notation (e.g., '1d4') and return the number of dice and sides."""
    match = re.match(r"(\d+)d(\d+)", dice_str)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 0

def combine_dice(dice_list):
    """Combine dice rolls into a single dice notation."""
    total_count = sum(dice[0] for dice in dice_list)
    if dice_list:
        sides = dice_list[0][1]
        return f"{total_count}d{sides}"
    return "0d0"

def calculate():
    """Calculate the total DC and detailed output based on selected reagents. If something is calculating wrong its probably this function."""
    selected_reagents = []
    for dropdown in ingredient_dropdowns:
        selection = dropdown.get()
        if selection:
            #split selection into name, category, and rarity
            name, rest = selection.split(" (")
            category, rarity = rest.split(", ")
            rarity = rarity.rstrip(")")  # Remove trailing parenthesis

            #match json based on name, category, and rarity
            reagent = next(
                (r for r in reagents if r["name"] == name and r["category"] == category and r["rarity"] == rarity),
                None
            )
            if reagent:
                selected_reagents.append(reagent)


    total_dc = 10  #base dc
    total_value = 0  #base value

    #base lists init
    curative_reagents = []
    damage_reagents = []
    modifiers = []
    effects = []

    #duration to rarity mapping
    RARITY_TO_DURATION = {
        "Common": 1,
        "Uncommon": 4,
        "Rare": 8,
        "Very Rare": 16,
        "Legendary": 24,
    }
    def parse_value(value):
            return int(value[:-2])  #remove gp from value in json and convert to an int
    
    #process each reagent
    for reagent in selected_reagents:
        total_dc += reagent["dc"]
        total_value += parse_value(reagent["value"]) 

        if reagent["type"] == "heal":
            curative_reagents.append(reagent)

        elif reagent["type"] == "damage":
            damage_reagents.append(reagent)

        elif reagent["type"] == "modifier":
            modifiers.append(reagent)

        elif reagent["type"] == "effect":
            effects.append(reagent["effect"])


    #output list init
    output_lines = []

    #Case 1: Curative + Damage/Modifier (Resistance Potion)
    if curative_reagents and (damage_reagents or modifiers):
        resistance_type = (
            damage_reagents[0]["effect"].split()[0]
            if damage_reagents else modifiers[0]["effect"].split()[-1]
        )
        #calc duration based on curative rarities
        total_duration = sum(RARITY_TO_DURATION[r["rarity"]] for r in curative_reagents)
        output_lines.append(f"Type: Resistance")
        output_lines.append(f"Effect: {resistance_type} Resistance")
        output_lines.append(f"Duration: {total_duration} hours\n")

        #clear damage reagents to prevent further processing
        damage_reagents = []

    #Case 2: All Curative
    elif curative_reagents and not (damage_reagents or modifiers):
        combined_dice = combine_dice([parse_dice(r["damage"]) for r in curative_reagents])
        output_lines.append(f"Type: Healing")
        output_lines.append(f"Effect: Healing")
        output_lines.append(f"Amount: {combined_dice}\n")

    #combine and modify damage effects
    final_damage_effects = {}
    for damage in damage_reagents:
        dice = parse_dice(damage["damage"])
        damage_type = damage["effect"]

        for modifier in modifiers:
            if "Change Damage Type to" in modifier["effect"]:
                new_type = modifier["effect"].split("Change Damage Type to ")[1]
                damage_type = f"{new_type} Damage"

        if damage_type not in final_damage_effects:
            final_damage_effects[damage_type] = []
        final_damage_effects[damage_type].append(dice)

    for effect, dice_list in final_damage_effects.items():
        combined_dice = combine_dice(dice_list)
        output_lines.append(f"Type: Damage")
        output_lines.append(f"Effect: {effect}")
        output_lines.append(f"Amount: {combined_dice}\n")

    #add exotic and additional effects regardless
    for effect in effects:
        output_lines.append(f"Effect: {effect}\n")

    #add the total DC to the output
    output_lines.append(f"Total DC: {total_dc}")
    output_lines.append(f"Total Value: {total_value}gp")

    #handle empty output
    if not output_lines:
        output_lines.append("No valid reagents selected or potion cannot be crafted.")

    #update results label
    result_label.config(text="\n".join(output_lines))

def update_dropdowns(container_type):
    """function to update dropdowns based on container selected"""
    num_dropdowns = 4 if container_type == "glass" else 5 if container_type == "crystal" else 0

    #clear existing dropdowns and the tracking list
    for widget in dropdown_frame.winfo_children():
        widget.destroy()
    ingredient_dropdowns.clear()

    if num_dropdowns == 0:
        return

    for i in range(num_dropdowns):
        ttk.Label(dropdown_frame, text=f"Ingredient {i + 1}:").grid(row=i, column=0, padx=5, pady=5)
        dropdown = ttk.Combobox(
            dropdown_frame,
            values=[
                f"{r['name']} ({r['category']}, {r['rarity']})" for r in reagents
            ],
            state="readonly",
            width=40
        )
        dropdown.grid(row=i, column=1, padx=5, pady=5)
        ingredient_dropdowns.append(dropdown)

def clear_dropdowns():
    """clear all dropdowns"""
    for dropdown in ingredient_dropdowns:
        dropdown.set("")
    result_label.config(text="")

#main app
root = tk.Tk()
root.resizable(False, False)
root.title("Alchemy Crafting Calculator")

#container dropdown
ttk.Label(root, text="Container Type:").grid(row=0, column=0, padx=10, pady=10)
container_type = ttk.Combobox(root, values=["glass", "crystal"], state="readonly")
container_type.grid(row=0, column=1, padx=10, pady=10)

#dropdown list init
ingredient_dropdowns = []

#frame for dynamic dropdowns
dropdown_frame = ttk.Frame(root)
dropdown_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

#kick off function if a container is selected
container_type.bind("<<ComboboxSelected>>", lambda event: update_dropdowns(container_type.get()))

#calc button
calculate_button = ttk.Button(root, text="Calculate", command=calculate)
calculate_button.grid(row=2, column=0, pady=10)

#clear button
clear_button = ttk.Button(root, text="Clear", command=clear_dropdowns)
clear_button.grid(row=2, column=1, pady=10)

#result label
result_label = ttk.Label(root, text="Effects: \nTotal DC: ")
result_label.grid(row=3, column=0, columnspan=2, pady=10)

root.mainloop()