"""
Agent-based NetLogo-like model with selectable from GUI.
Features:
- Grid with resource-patches (food patches) and gaps.
- Agents move stepwise across grid (can be inside gaps and die while crossing).
- Three strategies:
    cooperator  -> eattype 'low'  (harvest 50%), shares dispersal cost
    conditional -> eattype 'high' (harvest 99%), shares dispersal cost
    defector    -> eattype 'high' (harvest 99%), pays full dispersal cost
- Dispersal cost is applied only when an agent moves to a gap patch.
- For cooperators and conditionals, the cost is divided by the number of flockmates of the same strategy, within group_dispersal_range (plus 1 for the agent itself).
- Color coding: cooperator=green, conditional=blue, defector=red
- Results saved automatically when simulation finishes.
"""

import numpy as np
import random
import math
import os
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import tkinter as tk
from tkinter import messagebox
import matplotlib.patches as mpatches

# ---------------- Model classes ----------------

class Patch:
    def __init__(self):
        self.is_gap = True
        self.seedpatch = False
        self.seedpatchnum = None
        self.foodpatch = False
        self.foodpatchnum = None
        self.assortindex = 0.0
        self.resource = 0.0

class AgentModel:
    def __init__(self, width=112, height=112,
                 initial_agents=80, percent_cooperators=50, percent_conditionals=20,
                 patch_width=4, gap_size=20,
                 carrying_capacity=10, growth_rate=0.2,
                 living_costs=1, dispersal_cost=8, group_dispersal_range=30,
                 mutation_rate=0.0, cost_child=10,
                 results_prefix="simulation_results", random_seed=None):
        # parameters
        self.width = width
        self.height = height
        self.initial_agents = initial_agents
        self.percent_cooperators = percent_cooperators
        self.percent_conditionals = percent_conditionals
        self.patch_width = patch_width
        self.gap_size = gap_size
        self.carrying_capacity = carrying_capacity
        self.growth_rate = growth_rate
        self.living_costs = living_costs
        self.dispersal_cost = dispersal_cost
        self.group_dispersal_range = group_dispersal_range
        self.mutation_rate = mutation_rate
        self.cost_child = cost_child
        self.results_prefix = results_prefix
        self.run_seed = random_seed

        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

        # snapshot of params for logging
        self.params_snapshot = {
            "width": width, "height": height,
            "initial_agents": initial_agents,
            "percent_cooperators": percent_cooperators,
            "percent_conditionals": percent_conditionals,
            "patch_width": patch_width, "gap_size": gap_size,
            "carrying_capacity": carrying_capacity, "growth_rate": growth_rate,
            "living_costs": living_costs, "dispersal_cost": dispersal_cost,
            "group_dispersal_range": group_dispersal_range,
            "mutation_rate": mutation_rate, "cost_child": cost_child,
            "results_prefix": results_prefix, "random_seed": random_seed
        }
        print("[PARAMS]", self.params_snapshot)

        # grid
        self.grid = [[Patch() for _ in range(self.height)] for _ in range(self.width)]

        # agents list
        self.agents = []
        self.next_agent_id = 0

        # statistics
        self.stats = {'cooperators': [], 'conditionals': [], 'defectors': [], 'total_resources': [], 'steps': []}

        # Counters for migration deaths and successful migrations
        self.migration_deaths = {'cooperator': 0, 'conditional': 0, 'defector': 0}
        self.successful_migrations = {'cooperator': 0, 'conditional': 0, 'defector': 0}

        # create world and agents
        self.setup_world_netlogo_style()
        self.setup_agents_from_params()

    # ---------- world setup ----------
    def setup_world_netlogo_style(self):
        centers = []
        i = 0
        while True:
            cx = (self.gap_size // 2) + i * (self.gap_size + self.patch_width)
            if cx >= self.width: break
            j = 0
            while True:
                cy = (self.gap_size // 2) + j * (self.gap_size + self.patch_width)
                if cy >= self.height: break
                centers.append((cx, cy))
                j += 1
            i += 1

        for k, (cx, cy) in enumerate(centers):
            if 0 <= cx < self.width and 0 <= cy < self.height:
                p = self.grid[cx][cy]
                p.seedpatch = True
                p.seedpatchnum = k

        for x in range(self.width):
            for y in range(self.height):
                for k, (cx, cy) in enumerate(centers):
                    if math.hypot(x - cx, y - cy) <= self.patch_width:
                        cell = self.grid[x][y]
                        cell.is_gap = False
                        cell.foodpatch = True
                        cell.foodpatchnum = k
                        cell.resource = float(self.carrying_capacity)
                        break
                else:
                    self.grid[x][y].is_gap = True
                    self.grid[x][y].foodpatch = False
                    self.grid[x][y].resource = 0.0

    # ---------- agent setup ----------
    def setup_agents_from_params(self):
        food_positions = [(x, y) for x in range(self.width) for y in range(self.height) if self.grid[x][y].foodpatch]
        if not food_positions:
            raise RuntimeError("No foodpatches created — adjust patch_width/gap_size/world size")

        n_coop = round(self.initial_agents * self.percent_cooperators / 100)
        n_cond = round(self.initial_agents * self.percent_conditionals / 100)
        n_def = self.initial_agents - n_coop - n_cond
        if n_def < 0:
            n_def = 0

        colors = {"cooperator": "green", "conditional": "blue", "defector": "red"}

        def spawn(n, strategy):
            for _ in range(n):
                x, y = random.choice(food_positions)
                eattype = 'low' if strategy == 'cooperator' else 'high'
                self.agents.append({
                    'id': self.next_agent_id,
                    'strategy': strategy,
                    'position': (x, y),
                    'energy': 5.0,
                    'eattype': eattype,
                    'alive': True,
                    'mypatch': self.grid[x][y].foodpatchnum,
                    'color': colors[strategy]
                })
                self.next_agent_id += 1
        spawn(n_coop, 'cooperator')
        spawn(n_cond, 'conditional')
        spawn(n_def, 'defector')

    # ---------- helpers ----------
    def neighbors_coords(self, x, y, radius=1):
        pts = []
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and not (dx == 0 and dy == 0):
                    pts.append((nx, ny))
        return pts

    # ---------- step ----------
    def step(self):
        random.shuffle(self.agents)
        for agent in self.agents:
            if not agent['alive']:
                continue
            x, y = agent['position']
            old_patch = agent['mypatch']

            # flockmates: same strategy, within group_dispersal_range
            flockmates = [a for a in self.agents if a['alive'] and a['strategy'] == agent['strategy']
                          and math.hypot(a['position'][0] - x, a['position'][1] - y) <= self.group_dispersal_range
                          and a is not agent]

            # movement: align with NetLogo's move procedure
            neighbors = self.neighbors_coords(x, y, radius=2)
            # filter unoccupied neighbors
            free_neighbors = [(nx, ny) for (nx, ny) in neighbors
                             if not any(a['alive'] and a['position'] == (nx, ny) for a in self.agents if a is not agent)]
            if free_neighbors:
                # find patch with max resources where resource >= living_costs
                valid_neighbors = [(nx, ny) for (nx, ny) in free_neighbors
                                  if self.grid[nx][ny].resource >= self.living_costs]
                if valid_neighbors:
                    # move to patch with highest resources
                    best_patch = max(valid_neighbors, key=lambda p: self.grid[p[0]][p[1]].resource, default=None)
                    newx, newy = best_patch
                else:
                    # move to random unoccupied neighbor
                    newx, newy = random.choice(free_neighbors)
                # apply move
                agent['position'] = (newx, newy)
                cell = self.grid[newx][newy]
                if cell.foodpatch:
                    agent['mypatch'] = cell.foodpatchnum
                    if old_patch is not None and old_patch != agent['mypatch']:
                        self.successful_migrations[agent['strategy']] += 1
                # apply dispersal cost if in gap
                if cell.is_gap:
                    flock_count = 1 + len(flockmates)
                    if agent['strategy'] != 'defector':
                        cost = float(self.dispersal_cost) / float(flock_count)
                    else:
                        cost = float(self.dispersal_cost)
                    agent['energy'] -= cost
                    if agent['energy'] <= 0:
                        self.migration_deaths[agent['strategy']] += 1
                        agent['alive'] = False
                        continue

            # harvest (only on foodpatch)
            self.harvest(agent)
            # living cost
            agent['energy'] -= self.living_costs
            if agent['energy'] <= 0:
                agent['alive'] = False

            # reproduction
            self.reproduce(agent)

        # regrow resources
        self.regrow()

    def harvest(self, agent):
        if not agent['alive']:
            return
        x, y = agent['position']
        cell = self.grid[x][y]
        if not cell.foodpatch:
            return
        res = cell.resource
        if res <= 0:
            return
        if agent['eattype'] == 'low':
            take = 0.5 * res
        else:
            take = 0.99 * res
        cell.resource = max(0.0, res - take)
        agent['energy'] += take

    def reproduce(self, agent):
        if agent['energy'] < self.cost_child:
            return
        prob = 0.0005 * agent['energy']
        if random.random() > prob:
            return
        x, y = agent['position']
        neigh = self.neighbors_coords(x, y, radius=1)
        free = [p for p in neigh if not any(a['alive'] and a['position'] == p for a in self.agents)]
        if not free:
            return
        dest = random.choice(free)
        strat = agent['strategy']
        eattype = 'low' if strat == 'cooperator' else 'high'
        colors = {"cooperator": "green", "conditional": "blue", "defector": "red"}
        child = {
            'id': self.next_agent_id,
            'strategy': strat,
            'position': dest,
            'energy': float(self.cost_child),
            'eattype': eattype,
            'alive': True,
            'mypatch': self.grid[dest[0]][dest[1]].foodpatchnum if self.grid[dest[0]][dest[1]].foodpatch else None,
            'color': colors[strat]
        }
        if random.random() < self.mutation_rate:
            child['strategy'] = random.choice(['cooperator', 'conditional', 'defector'])
            child['eattype'] = 'low' if child['strategy'] == 'cooperator' else 'high'
            child['color'] = colors[child['strategy']]
        self.agents.append(child)
        self.next_agent_id += 1
        agent['energy'] -= self.cost_child

    def regrow(self):
        for x in range(self.width):
            for y in range(self.height):
                cell = self.grid[x][y]
                if cell.foodpatch:
                    r = cell.resource
                    if r >= 0.1:
                        g = self.growth_rate * r * (1 - r / self.carrying_capacity)
                        cell.resource = min(r + g, self.carrying_capacity)
                    else:
                        cell.resource = 0.1

    def collect_stats(self, step):
        coop = sum(1 for a in self.agents if a['alive'] and a['strategy'] == 'cooperator')
        cond = sum(1 for a in self.agents if a['alive'] and a['strategy'] == 'conditional')
        defe = sum(1 for a in self.agents if a['alive'] and a['strategy'] == 'defector')
        total_res = sum(self.grid[x][y].resource for x in range(self.width) for y in range(self.height) if self.grid[x][y].foodpatch)
        self.stats['cooperators'].append(coop)
        self.stats['conditionals'].append(cond)
        self.stats['defectors'].append(defe)
        self.stats['total_resources'].append(total_res)
        self.stats['steps'].append(step)

    def save_results(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(script_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        
        fname = os.path.join(results_dir, f"{self.results_prefix}.txt")
        print(f"Saving text results to: {fname}")
        with open(fname, 'w', encoding='utf-8') as f:
            f.write("Simulation Results\n\nParameters:\n")
            for k, v in self.params_snapshot.items():
                f.write(f"  {k}: {v}\n")
            f.write("\nSummary:\n")
            if self.stats['steps']:
                f.write(f"Number of Steps recorded: {len(self.stats['steps'])}\n")
                f.write(f"Cooperators: {self.stats['cooperators'][-1]}\n")
                f.write(f"Conditionals: {self.stats['conditionals'][-1]}\n")
                f.write(f"Defectors: {self.stats['defectors'][-1]}\n")
                f.write(f"Total Resources: {self.stats['total_resources'][-1]:.2f}\n")

        plt.figure(figsize=(10, 6))
        plt.plot(self.stats['steps'], self.stats['cooperators'], 'g-', label='Cooperators (low harvest, share migration)')
        plt.plot(self.stats['steps'], self.stats['conditionals'], 'b-', label='Conditional Defector (high harvest, share migration)')
        plt.plot(self.stats['steps'], self.stats['defectors'], 'r-', label='Defector (high harvest, no migration help)')
        plt.title('Agent Population Evolution')
        plt.xlabel('Step')
        plt.ylabel('Number')
        plt.legend()
        plt.grid(True)
        agent_plot_path = os.path.join(results_dir, f"{self.results_prefix}_agents.png")
        plt.savefig(agent_plot_path)
        print(f"Saving agent population plot to: {agent_plot_path}")
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.plot(self.stats['steps'], self.stats['total_resources'], 'k-', label='Total Resources')
        plt.title('Total Resources Evolution')
        plt.xlabel('Step')
        plt.ylabel('Resources')
        plt.legend()
        plt.grid(True)
        resources_plot_path = os.path.join(results_dir, f"{self.results_prefix}_resources.png")
        plt.savefig(resources_plot_path)
        print(f"Saving resources plot to: {resources_plot_path}")
        plt.close()

        plt.figure(figsize=(8, 6))
        categories = ['Cooperators', 'Conditionals', 'Defectors']
        values = [
            self.stats['cooperators'][-1],
            self.stats['conditionals'][-1],
            self.stats['defectors'][-1]
        ]
        colors = ['green', 'blue', 'red']
        bars = plt.bar(categories, values, color=colors)
        plt.title(f'Final Agent Populations (Step {len(self.stats["steps"])})')
        plt.ylabel('Number of Agents')
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom')
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        summary_plot_path = os.path.join(results_dir, f"{self.results_prefix}_summary.png")
        plt.savefig(summary_plot_path)
        print(f"Saving summary bar chart to: {summary_plot_path}")
        plt.close()

        plt.figure(figsize=(6, 6))
        total_res = max(0.0, self.stats['total_resources'][-1])
        plt.bar(['Total Resources'], [total_res], color='black')
        plt.title(f'Final Total Resources (Step {len(self.stats["steps"])})')
        plt.ylabel('Resources')
        text_y = total_res + (100 if total_res > 0 else 1000)
        plt.text(0, text_y, f"{total_res:.2f}", ha='center', va='bottom')
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        resources_bar_path = os.path.join(results_dir, f"{self.results_prefix}_resources_bar.png")
        plt.savefig(resources_bar_path)
        print(f"Saving resources bar chart to: {resources_bar_path}")
        plt.close()

        plt.figure(figsize=(10, 6))
        categories = ['Coop Deaths', 'Cond Deaths', 'Def Deaths', 'Coop Success', 'Cond Success', 'Def Success']
        values = [
            self.migration_deaths['cooperator'],
            self.migration_deaths['conditional'],
            self.migration_deaths['defector'],
            self.successful_migrations['cooperator'],
            self.successful_migrations['conditional'],
            self.successful_migrations['defector']
        ]
        colors = ['darkgreen', 'darkblue', 'darkred', 'green', 'blue', 'red']
        bars = plt.bar(categories, values, color=colors)
        plt.title('Migration Deaths and Successful Migrations by Agent Type')
        plt.ylabel('Number')
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom')
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        migration_plot_path = os.path.join(results_dir, f"{self.results_prefix}_migrations.png")
        plt.savefig(migration_plot_path)
        print(f"Saving migration and death bar chart to: {migration_plot_path}")
        plt.close()

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Simulation Summary</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h2>Simulation Summary</h2>
    <canvas id="summaryChart" width="400" height="300"></canvas>
    <script>
        const ctx = document.getElementById('summaryChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: ['Cooperators', 'Conditionals', 'Defectors'],
                datasets: [{{
                    label: 'Agent Populations',
                    data: [{self.stats['cooperators'][-1]}, {self.stats['conditionals'][-1]}, {self.stats['defectors'][-1]}],
                    backgroundColor: ['#00FF00', '#0000FF', '#FF0000'],
                    borderColor: ['#00CC00', '#0000CC', '#CC0000'],
                    borderWidth: 1
                }}]
            }},
            options: {{
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Final Agent Populations (Step {len(self.stats['steps'])})'
                    }},
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Number of Agents'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        html_fname = os.path.join(results_dir, f"{self.results_prefix}_summary.html")
        with open(html_fname, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saving interactive chart to: {html_fname}")

# ---------------- Animation ----------------
def animate_simulation(model, steps=1000, steps_per_frame=1, interval=100, show_energy=False):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    grid = np.zeros((model.width, model.height))
    im = ax1.imshow(grid.T, origin='lower', cmap='YlGn', vmin=0, vmax=model.carrying_capacity)
    scatter = ax1.scatter([], [], s=20)
    ax1.set_xlim(-0.5, model.width - 0.5)
    ax1.set_ylim(-0.5, model.height - 0.5)
    ax1.set_title("Step 0")
    fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)

    ax2.set_title('Agent Population Evolution')
    ax2.set_xlabel('Step')
    ax2.set_ylabel('Number')
    line_coop, = ax2.plot([], [], 'g-', label='Cooperators (low harvest, share migration)')
    line_cond, = ax2.plot([], [], 'b-', label='Conditional Defector (high harvest, share migration)')
    line_def, = ax2.plot([], [], 'r-', label='Defector (high harvest, no migration help)')
    ax2.legend()
    ax2.grid(True)
    ax2.set_xlim(0, steps)
    ax2.set_ylim(0, model.initial_agents * 5)

    colors_map = {"cooperator": "green", "conditional": "blue", "defector": "red"}

    global energy_texts
    energy_texts = []
    for agent in model.agents:
        t = ax1.text(agent['position'][0], agent['position'][1] + 1,
                     f"{int(agent['energy'])}",
                     color="black", ha="center", va="bottom",
                     fontsize=7, fontweight="bold", visible=False)
        energy_texts.append(t)

    total_frames = max(1, steps // steps_per_frame)

    def update(frame):
        for i in range(steps_per_frame):
            current_step = frame * steps_per_frame + i
            if current_step >= steps:
                ani.event_source.stop()
                model.save_results()
                print(f"Simulation finished. Results saved with prefix: {model.results_prefix}")
                return

            model.step()
            model.collect_stats(current_step)

        for x in range(model.width):
            for y in range(model.height):
                cell = model.grid[x][y]
                grid[x, y] = cell.resource if cell.foodpatch else 0.0
        im.set_data(grid.T)

        xs = [a['position'][0] for a in model.agents if a['alive']]
        ys = [a['position'][1] for a in model.agents if a['alive']]
        cs = [colors_map[a['strategy']] for a in model.agents if a['alive']]
        if xs and ys:
            scatter.set_offsets(np.c_[xs, ys])
            scatter.set_color(cs)
        else:
            scatter.set_offsets([])

        if show_energy:
            while len(energy_texts) < len(model.agents):
                t = ax1.text(0, 0, "", color="black",
                             ha="center", va="bottom",
                             fontsize=7, fontweight="bold",
                             visible=False)
                energy_texts.append(t)

            for i, agent in enumerate(model.agents):
                if agent['alive']:
                    x, y = agent['position']
                    energy_texts[i].set_position((x, y + 1))
                    energy_texts[i].set_text(f"{int(agent['energy'])}")
                    energy_texts[i].set_visible(True)
                else:
                    energy_texts[i].set_visible(False)
        else:
            for t in energy_texts:
                t.set_visible(False)

        # Corrected lines: use model.stats instead of self.stats
        line_coop.set_data(model.stats['steps'], model.stats['cooperators'])
        line_cond.set_data(model.stats['steps'], model.stats['conditionals'])
        line_def.set_data(model.stats['steps'], model.stats['defectors'])

        ax1.set_title(f"Step {frame * steps_per_frame + 1}")
        return scatter, im, line_coop, line_cond, line_def, *energy_texts

    ani = animation.FuncAnimation(fig, update, frames=total_frames + 1,
                                  interval=interval, blit=False, repeat=False)

    def on_close(event):
        model.save_results()
        print("Window closed: results saved.")
    fig.canvas.mpl_connect('close_event', on_close)

    plt.tight_layout()
    plt.show()

def run_simulation_with_params():
    global root, entries, show_energy_labels
    root = tk.Tk()
    root.title("Agent-based Model Parameters")
    show_energy_labels = tk.BooleanVar(value=False)

    labels = [
        "width", "height", "initial_agents",
        "percent_cooperators", "percent_conditionals",
        "patch_width", "gap_size", "carrying_capacity",
        "growth_rate", "living_costs", "dispersal_cost",
        "group_dispersal_range", "mutation_rate", "cost_child",
        "steps", "steps_per_frame", "random_seed", "results_prefix"
    ]

    defaults = {
        "width": 112, "height": 112, "initial_agents": 80,
        "percent_cooperators": 50, "percent_conditionals": 20,
        "patch_width": 4, "gap_size": 20, "carrying_capacity": 10,
        "growth_rate": 0.2, "living_costs": 1, "dispersal_cost": 8,
        "group_dispersal_range": 30, "mutation_rate": 0.0,
        "cost_child": 10, "steps": 1000, "steps_per_frame": 1,
        "random_seed": "", "results_prefix": "simulation_results"
    }

    entries = {}
    for i, label in enumerate(labels):
        tk.Label(root, text=label).grid(row=i, column=0, sticky="w")
        e = tk.Entry(root)
        e.grid(row=i, column=1)
        e.insert(0, str(defaults[label]))
        entries[label] = e

    def start_simulation():
        try:
            params = {
                'width': int(entries['width'].get()),
                'height': int(entries['height'].get()),
                'initial_agents': int(entries['initial_agents'].get()),
                'percent_cooperators': float(entries['percent_cooperators'].get()),
                'percent_conditionals': float(entries['percent_conditionals'].get()),
                'patch_width': int(entries['patch_width'].get()),
                'gap_size': int(entries['gap_size'].get()),
                'carrying_capacity': float(entries['carrying_capacity'].get()),
                'growth_rate': float(entries['growth_rate'].get()),
                'living_costs': float(entries['living_costs'].get()),
                'dispersal_cost': float(entries['dispersal_cost'].get()),
                'group_dispersal_range': float(entries['group_dispersal_range'].get()),
                'mutation_rate': float(entries['mutation_rate'].get()),
                'cost_child': float(entries['cost_child'].get()),
                'results_prefix': entries['results_prefix'].get()
            }
            seed_text = entries['random_seed'].get().strip()
            seed_val = int(seed_text) if seed_text != "" else None
            steps = int(entries['steps'].get())
            steps_per_frame = int(entries['steps_per_frame'].get())

            root.destroy()
            model = AgentModel(**params, random_seed=seed_val)
            animate_simulation(
                model,
                steps=steps,
                steps_per_frame=steps_per_frame,
                interval=100,
                show_energy=show_energy_labels.get()
            )
        except Exception as e:
            messagebox.showerror("Input Error", str(e))

    row = len(labels)
    tk.Checkbutton(root, text="Show agent energy", variable=show_energy_labels).grid(row=row, column=0, sticky="w")
    row += 1
    tk.Button(root, text="Start Simulation", command=start_simulation).grid(row=row, column=0, columnspan=2, pady=8)

    root.mainloop()

if __name__ == "__main__":
    run_simulation_with_params()