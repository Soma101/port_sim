# port_sim.py
import streamlit as st
import numpy as np
import random
import json
import os
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# --- Container & Ship Classes ---

class Container:
    def __init__(self, weight, size, import_export, category):
        self.weight = weight
        self.size = size
        self.import_export = import_export
        self.category = category

    def __repr__(self):
        return f"Container({self.weight}, {self.size}, {self.import_export}, {self.category})"

class Ship:
    _history_file = ".venv/ship_history.json"
    _history = {}

    # Load historical data
    if os.path.exists(_history_file):
        with open(_history_file, "r") as f:
            _history = json.load(f)
            _history = {str(k): list(map(int, v)) for k, v in _history.items()}

    def __init__(self, name, container_count=0, delay=None):
        self.name = name
        self.containers = [random_container() for _ in range(container_count)]
        self.delay = self._assign_delay(delay)
        self._store_history()
        self._save_history_to_file()

    def _assign_delay(self, delay):
        if delay is not None:
            return delay
        if self.name in Ship._history and Ship._history[self.name]:
            return round(sum(Ship._history[self.name]) / len(Ship._history[self.name]))
        return 0

    def _store_history(self):
        if self.name not in Ship._history:
            Ship._history[self.name] = []
        Ship._history[self.name].append(self.delay)

    def _save_history_to_file(self):
        with open(Ship._history_file, "w") as f:
            json.dump(Ship._history, f)

    @classmethod
    def get_history(cls):
        return cls._history

    def __repr__(self):
        return f"Ship(Name: {self.name}, Delay: {self.delay}, Containers: {len(self.containers)})"

# --- Helper Functions ---

def random_container():
    weight = random.randint(500, 2000)
    size = 1
    import_export = random.choice(["import", "export"])
    category = random.choice(["Reefer", "Hazardous", "Normal"])
    return Container(weight, size, import_export, category)

def draw_yard(yard):
    cmap = ListedColormap(['white', 'yellow', 'orange', 'red'])
    plt.figure(figsize=(6, 6))
    plt.imshow(yard, cmap=cmap, origin='upper', vmin=0, vmax=3)
    rows, cols = yard.shape
    for i in range(rows):
        for j in range(cols):
            plt.text(j, i, str(yard[i, j]), ha='center', va='center', color='black', fontsize=12)
    plt.title("Port Yard - Container Stack Heights")
    plt.xlabel("Column")
    plt.ylabel("Row")
    plt.colorbar(ticks=[0, 1, 2, 3], label="Stack Height")
    st.pyplot(plt)
    plt.close()

def place_containers(yard, ships):
    rows, cols = yard.shape
    max_stack = 3

    # Count total imports/exports
    total_imports = sum(len([c for c in ship.containers if c.import_export=="import"]) for ship in ships)
    total_exports = sum(len([c for c in ship.containers if c.import_export=="export"]) for ship in ships)
    total_containers = total_imports + total_exports

    import_cols_count = max(1, int(cols * (total_imports / total_containers))) if total_containers>0 else cols
    import_cols = list(range(import_cols_count))
    export_cols = list(range(import_cols_count, cols))

    ships = sorted(ships, key=lambda s: s.delay)

    def allocate_rows(containers_count):
        categories = ["Reefer","Hazardous","Normal"]
        cat_counts = [len([c for s in ships for c in s.containers if c.import_export=="import" and c.category==cat]) for cat in categories]
        total = sum(cat_counts)
        if total == 0:
            return {cat: (0,0) for cat in categories}
        row_alloc = {}
        start = 0
        for cat, count in zip(categories, cat_counts):
            end = start + max(1, int(round(rows * count / total)))
            row_alloc[cat] = (start, min(end, rows))
            start = end
        return row_alloc

    import_row_alloc = allocate_rows(total_imports)
    export_row_alloc = allocate_rows(total_exports)

    for ship in ships:
        groups = {"import": [], "export": []}
        for c in ship.containers:
            groups[c.import_export].append(c)

        for group_type, containers in groups.items():
            if not containers:
                continue

            cols_range = import_cols if group_type=="import" else export_cols
            row_alloc = import_row_alloc if group_type=="import" else export_row_alloc

            for cat in ["Reefer","Hazardous","Normal"]:
                cat_group = [c for c in containers if c.category==cat]
                cat_group.sort(key=lambda x: x.weight, reverse=True)

                for container in cat_group:
                    placed = False
                    r_start, r_end = row_alloc[cat]
                    if r_end <= r_start:
                        r_start, r_end = 0, rows
                    row_order = list(range(r_start, r_end)) if group_type=="import" else list(range(r_start, r_end))
                    for r in row_order:
                        for c in cols_range:
                            if yard[r,c]<max_stack:
                                yard[r,c]+=1
                                placed=True
                                break
                        if placed:
                            break
                    if not placed:
                        for r in range(rows):
                            for c in range(cols):
                                if yard[r,c]<max_stack:
                                    yard[r,c]+=1
                                    placed=True
                                    break
                            if placed:
                                break
    return yard

# --- Streamlit App ---

st.title("Port Container Yard Simulator")

yard_rows = st.number_input("Yard rows", min_value=1, max_value=20, value=5)
yard_cols = st.number_input("Yard columns", min_value=1, max_value=20, value=5)
num_ships = st.number_input("Number of ships", min_value=1, max_value=4, value=2)

ships = []
for i in range(num_ships):
    name = st.text_input(f"Ship {i+1} name", f"Vessel{i+1}")
    containers = st.number_input(f"Number of containers on {name}", min_value=1, max_value=100, value=10)
    delay = st.number_input(f"Delay in hours for {name} (0 if unknown)", min_value=0, max_value=24, value=0)
    if name:
        ships.append(Ship(name=name, container_count=containers, delay=delay))

if st.button("Run Simulation") and ships:
    yard = np.zeros((yard_rows, yard_cols), dtype=int)
    final_yard = place_containers(yard, ships)
    st.write("### Final Yard Array")
    st.write(final_yard)

    st.write("### Yard Heatmap")
    draw_yard(final_yard)

    st.write("### Historical Ship Delays")
    st.write(Ship.get_history())