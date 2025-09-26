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
- For cooperators and conditionals, the cost is divided by the number of flockmates of the same strategy,
 within group_dispersal_range (plus 1 for the agent itself).
- Color coding: cooperator=green, conditional=blue, defector=red
- Results saved automatically when simulation finishes.
- Comprehensive debugging and logging system.
- Anti-loop movement system to prevent agents getting stuck.
"""

import numpy as np
import random
import math
import os
import time
import logging
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import tkinter as tk
from tkinter import messagebox
import matplotlib.patches as mpatches
from collections import defaultdict, deque

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------- Enhanced Model classes ----------------

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
                 initial_agents=80, percent_cooperators=60, percent_conditionals=10,
                 patch_width=4, gap_size=20,
                 carrying_capacity=10, growth_rate=0.2,
                 living_costs=1, dispersal_cost=8, group_dispersal_range=50,
                 mutation_rate=0.0, cost_child=10,
                 results_prefix="simulation_results", random_seed=None,
                 debug_mode=True):
        
        # Performance tracking
        self.start_time = time.time()
        self.debug_mode = debug_mode
        
        # Parameters
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

        # Snapshot of params for logging
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
        
        if self.debug_mode:
            logger.info(f"[PARAMS] {self.params_snapshot}")

        # Enhanced data structures for performance
        self.grid = [[Patch() for _ in range(self.height)] for _ in range(self.width)]
        
        # Numpy arrays for faster operations
        self.resource_grid = np.zeros((self.width, self.height), dtype=np.float32)
        self.is_gap_grid = np.ones((self.width, self.height), dtype=bool)
        self.foodpatch_grid = np.zeros((self.width, self.height), dtype=bool)
        
        # Agents list and spatial optimization
        self.agents = []
        self.next_agent_id = 0
        self.alive_agents_cache = []  # Cache for alive agents
        self.cache_valid = False
        
        # Agent movement history to prevent loops
        self.agent_movement_history = defaultdict(lambda: deque(maxlen=5))
        
        # Statistics
        self.stats = {
            'cooperators': [], 'conditionals': [], 'defectors': [], 
            'total_resources': [], 'steps': [], 'performance_metrics': []
        }

        # Enhanced tracking
        self.migration_deaths = {'cooperator': 0, 'conditional': 0, 'defector': 0}
        self.successful_migrations = {'cooperator': 0, 'conditional': 0, 'defector': 0}
        self.loop_prevention_moves = 0
        self.total_moves = 0

        # Create world and agents
        self.setup_world_netlogo_style()
        self.setup_agents_from_params()

    def get_alive_agents(self):
        """Cached access to alive agents for performance"""
        if not self.cache_valid:
            self.alive_agents_cache = [a for a in self.agents if a['alive']]
            self.cache_valid = True
        return self.alive_agents_cache

    def invalidate_cache(self):
        """Invalidate cache when agents die/born"""
        self.cache_valid = False

    # ---------- Enhanced world setup ----------
    def setup_world_netlogo_style(self):
        """Enhanced world setup with numpy optimization"""
        centers = []
        i = 0
        while True:
            cx = (self.gap_size // 2) + i * (self.gap_size + self.patch_width)
            if cx >= self.width: 
                break
            j = 0
            while True:
                cy = (self.gap_size // 2) + j * (self.gap_size + self.patch_width)
                if cy >= self.height: 
                    break
                centers.append((cx, cy))
                j += 1
            i += 1

        # Set seed patches
        for k, (cx, cy) in enumerate(centers):
            if 0 <= cx < self.width and 0 <= cy < self.height:
                p = self.grid[cx][cy]
                p.seedpatch = True
                p.seedpatchnum = k

        # Create circular food patches efficiently
        x_coords, y_coords = np.meshgrid(np.arange(self.width), np.arange(self.height), indexing='ij')
        
        for k, (cx, cy) in enumerate(centers):
            # Calculate distances using numpy for speed
            distances = np.sqrt((x_coords - cx)**2 + (y_coords - cy)**2)
            mask = distances <= self.patch_width
            
            # Apply mask to create food patches
            self.is_gap_grid[mask] = False
            self.foodpatch_grid[mask] = True
            self.resource_grid[mask] = float(self.carrying_capacity)
            
            # Update grid objects
            for x in range(max(0, cx - self.patch_width - 1), min(self.width, cx + self.patch_width + 2)):
                for y in range(max(0, cy - self.patch_width - 1), min(self.height, cy + self.patch_width + 2)):
                    if mask[x, y]:
                        cell = self.grid[x][y]
                        cell.is_gap = False
                        cell.foodpatch = True
                        cell.foodpatchnum = k
                        cell.resource = float(self.carrying_capacity)

        if self.debug_mode:
            total_food_patches = np.sum(self.foodpatch_grid)
            logger.info(f"Created {len(centers)} food patch centers, {total_food_patches} total food cells")

    # ---------- Agent setup ----------
    def setup_agents_from_params(self):
        """Enhanced agent setup with validation"""
        food_positions = [(x, y) for x in range(self.width) for y in range(self.height) 
                         if self.foodpatch_grid[x, y]]
        
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
                    'color': colors[strategy],
                    'last_positions': deque(maxlen=3),  # Track recent positions
                    'stuck_counter': 0  # Track if agent is stuck
                })
                self.next_agent_id += 1
        
        spawn(n_coop, 'cooperator')
        spawn(n_cond, 'conditional')
        spawn(n_def, 'defector')
        
        if self.debug_mode:
            logger.info(f"Created {n_coop} cooperators, {n_cond} conditionals, {n_def} defectors")

    # ---------- Enhanced movement helpers ----------
    def neighbors_coords_circular(self, x, y, radius=2):
        """Get neighbors in circular pattern (NetLogo-style)"""
        pts = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                # Check if within circular radius
                if math.sqrt(dx*dx + dy*dy) <= radius:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        pts.append((nx, ny))
        return pts

    def is_position_occupied(self, pos, exclude_agent=None):
        """Fast check if position is occupied"""
        for agent in self.get_alive_agents():
            if agent is not exclude_agent and agent['position'] == pos:
                return True
        return False

    def get_best_move_anti_loop(self, agent):
        """Enhanced movement with anti-loop mechanism"""
        x, y = agent['position']
        neighbors = self.neighbors_coords_circular(x, y, radius=2)
        
        # Filter unoccupied neighbors
        free_neighbors = [pos for pos in neighbors if not self.is_position_occupied(pos, agent)]
        
        if not free_neighbors:
            return None
            
        # Anti-loop mechanism: avoid recently visited positions
        recent_positions = agent['last_positions']
        if len(recent_positions) >= 2:
            # Prefer positions not recently visited
            non_recent = [pos for pos in free_neighbors if pos not in recent_positions]
            if non_recent:
                free_neighbors = non_recent
                self.loop_prevention_moves += 1

        # Find patch with max resources where resource >= living_costs
        valid_neighbors = []
        for nx, ny in free_neighbors:
            if self.resource_grid[nx, ny] >= self.living_costs:
                valid_neighbors.append((nx, ny))

        if valid_neighbors:
            # Move to patch with highest resources
            best_patch = max(valid_neighbors, key=lambda p: self.resource_grid[p[0], p[1]])
            return best_patch
        else:
            # Move to random unoccupied neighbor
            return random.choice(free_neighbors)

    # ---------- Enhanced step function ----------
    def step(self):
        """Enhanced step function with performance monitoring"""
        step_start = time.time()
        
        alive_agents = self.get_alive_agents()
        random.shuffle(alive_agents)
        
        moves_this_step = 0
        deaths_this_step = 0
        births_this_step = 0
        
        for agent in alive_agents:
            if not agent['alive']:
                continue
                
            x, y = agent['position']
            old_patch = agent['mypatch']

            # Enhanced flockmate finding with spatial optimization
            flockmates = self.find_flockmates_optimized(agent)

            # Enhanced movement
            new_pos = self.get_best_move_anti_loop(agent)
            if new_pos:
                newx, newy = new_pos
                
                # Update position and history
                agent['last_positions'].append(agent['position'])
                agent['position'] = (newx, newy)
                moves_this_step += 1
                self.total_moves += 1
                
                # Update patch info
                cell = self.grid[newx][newy]
                if cell.foodpatch:
                    agent['mypatch'] = cell.foodpatchnum
                    if old_patch is not None and old_patch != agent['mypatch']:
                        self.successful_migrations[agent['strategy']] += 1
                
                # Apply dispersal cost if in gap
                if self.is_gap_grid[newx, newy]:
                    flock_count = 1 + len(flockmates)
                    if agent['strategy'] != 'defector':
                        cost = float(self.dispersal_cost) / float(flock_count)
                    else:
                        cost = float(self.dispersal_cost)
                    
                    agent['energy'] -= cost
                    if agent['energy'] <= 0:
                        self.migration_deaths[agent['strategy']] += 1
                        agent['alive'] = False
                        deaths_this_step += 1
                        continue

            # Harvest (optimized)
            self.harvest_optimized(agent)
            
            # Living cost
            agent['energy'] -= self.living_costs
            if agent['energy'] <= 0:
                agent['alive'] = False
                deaths_this_step += 1
                continue

            # Reproduction
            if self.reproduce_optimized(agent):
                births_this_step += 1

        # Invalidate cache if agents died/born
        if deaths_this_step > 0 or births_this_step > 0:
            self.invalidate_cache()

        # Regrow resources (optimized)
        self.regrow_optimized()
        
        step_time = time.time() - step_start
        
        if self.debug_mode and hasattr(self, 'current_step'):
            if self.current_step % 100 == 0:  # Log every 100 steps
                logger.info(f"Step {self.current_step}: {len(self.get_alive_agents())} alive, "
                          f"{moves_this_step} moves, {deaths_this_step} deaths, {births_this_step} births, "
                          f"time: {step_time:.3f}s")

    def find_flockmates_optimized(self, agent):
        """Optimized flockmate finding"""
        x, y = agent['position']
        flockmates = []
        
        for other in self.get_alive_agents():
            if other is agent or not other['alive'] or other['strategy'] != agent['strategy']:
                continue
            ox, oy = other['position']
            distance = math.sqrt((x - ox)**2 + (y - oy)**2)
            if distance <= self.group_dispersal_range:
                flockmates.append(other)
        
        return flockmates

    def harvest_optimized(self, agent):
        """Optimized harvest function"""
        if not agent['alive']:
            return
        
        x, y = agent['position']
        if not self.foodpatch_grid[x, y]:
            return
            
        res = self.resource_grid[x, y]
        if res <= 0:
            return
            
        if agent['eattype'] == 'low':
            take = 0.5 * res
        else:
            take = 0.99 * res
            
        self.resource_grid[x, y] = max(0.0, res - take)
        self.grid[x][y].resource = self.resource_grid[x, y]  # Keep sync
        agent['energy'] += take

    def reproduce_optimized(self, agent):
        """Optimized reproduction with better neighbor finding"""
        if agent['energy'] < self.cost_child:
            return False
            
        prob = 0.0005 * agent['energy']
        if random.random() > prob:
            return False
            
        x, y = agent['position']
        neighbors = self.neighbors_coords_circular(x, y, radius=1)
        free = [p for p in neighbors if not self.is_position_occupied(p)]
        
        if not free:
            return False
            
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
            'mypatch': self.grid[dest[0]][dest[1]].foodpatchnum if self.foodpatch_grid[dest[0], dest[1]] else None,
            'color': colors[strat],
            'last_positions': deque(maxlen=3),
            'stuck_counter': 0
        }
        
        # Mutation
        if random.random() < self.mutation_rate:
            child['strategy'] = random.choice(['cooperator', 'conditional', 'defector'])
            child['eattype'] = 'low' if child['strategy'] == 'cooperator' else 'high'
            child['color'] = colors[child['strategy']]
            
        self.agents.append(child)
        self.next_agent_id += 1
        agent['energy'] -= self.cost_child
        
        return True

    def regrow_optimized(self):
        """Optimized resource regrowth using numpy"""
        # Use numpy for vectorized operations where possible
        mask = self.foodpatch_grid & (self.resource_grid >= 0.1)
        
        # Vectorized growth calculation
        r = self.resource_grid[mask]
        growth = self.growth_rate * r * (1 - r / self.carrying_capacity)
        self.resource_grid[mask] = np.minimum(r + growth, self.carrying_capacity)
        
        # Handle low resource patches
        low_mask = self.foodpatch_grid & (self.resource_grid < 0.1)
        self.resource_grid[low_mask] = 0.1
        
        # Sync with grid objects (only for changed patches)
        changed_mask = mask | low_mask
        for x in range(self.width):
            for y in range(self.height):
                if changed_mask[x, y]:
                    self.grid[x][y].resource = self.resource_grid[x, y]

    def collect_stats(self, step):
        """Enhanced statistics collection"""
        self.current_step = step  # Store for debugging
        
        alive_agents = self.get_alive_agents()
        coop = sum(1 for a in alive_agents if a['strategy'] == 'cooperator')
        cond = sum(1 for a in alive_agents if a['strategy'] == 'conditional')
        defe = sum(1 for a in alive_agents if a['strategy'] == 'defector')
        total_res = np.sum(self.resource_grid[self.foodpatch_grid])
        
        self.stats['cooperators'].append(coop)
        self.stats['conditionals'].append(cond)
        self.stats['defectors'].append(defe)
        self.stats['total_resources'].append(total_res)
        self.stats['steps'].append(step)
        
        # Performance metrics
        if hasattr(self, 'start_time'):
            runtime = time.time() - self.start_time
            self.stats['performance_metrics'].append({
                'step': step,
                'runtime': runtime,
                'agents_alive': len(alive_agents),
                'loop_prevention_ratio': self.loop_prevention_moves / max(1, self.total_moves)
            })

    def save_results(self):
        """Enhanced results saving with performance metrics"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(script_dir, "results")
        os.makedirs(results_dir, exist_ok=True)
        
        fname = os.path.join(results_dir, f"{self.results_prefix}.txt")
        logger.info(f"Saving text results to: {fname}")
        
        with open(fname, 'w', encoding='utf-8') as f:
            f.write("Enhanced Simulation Results\n\nParameters:\n")
            for k, v in self.params_snapshot.items():
                f.write(f"  {k}: {v}\n")
            
            f.write("\nPerformance Metrics:\n")
            if hasattr(self, 'start_time'):
                total_runtime = time.time() - self.start_time
                f.write(f"  Total runtime: {total_runtime:.2f} seconds\n")
                f.write(f"  Total moves: {self.total_moves}\n")
                f.write(f"  Loop prevention moves: {self.loop_prevention_moves}\n")
                f.write(f"  Loop prevention ratio: {self.loop_prevention_moves / max(1, self.total_moves):.3f}\n")
            
            f.write("\nFinal Results:\n")
            if self.stats['steps']:
                f.write(f"Number of Steps: {len(self.stats['steps'])}\n")
                f.write(f"Cooperators: {self.stats['cooperators'][-1]}\n")
                f.write(f"Conditionals: {self.stats['conditionals'][-1]}\n")
                f.write(f"Defectors: {self.stats['defectors'][-1]}\n")
                f.write(f"Total Resources: {self.stats['total_resources'][-1]:.2f}\n")
                
                f.write("\nMigration Statistics:\n")
                for strategy in ['cooperator', 'conditional', 'defector']:
                    f.write(f"  {strategy.capitalize()} - Deaths: {self.migration_deaths[strategy]}, "
                           f"Successful: {self.successful_migrations[strategy]}\n")

        # Save all the plots (same as before but with enhanced data)
        self._save_plots(results_dir)
        
        # Save performance metrics plot
        if self.stats['performance_metrics']:
            plt.figure(figsize=(10, 6))
            metrics = self.stats['performance_metrics']
            steps = [m['step'] for m in metrics]
            runtimes = [m['runtime'] for m in metrics]
            plt.plot(steps, runtimes, 'purple', label='Cumulative Runtime (s)')
            plt.title('Performance Over Time')
            plt.xlabel('Step')
            plt.ylabel('Cumulative Runtime (seconds)')
            plt.legend()
            plt.grid(True)
            perf_plot_path = os.path.join(results_dir, f"{self.results_prefix}_performance.png")
            plt.savefig(perf_plot_path)
            logger.info(f"Saving performance plot to: {perf_plot_path}")
            plt.close()

    def _save_plots(self, results_dir):
        """Save all visualization plots"""
        # Agent population evolution
        plt.figure(figsize=(10, 6))
        plt.plot(self.stats['steps'], self.stats['cooperators'], 'g-', label='Cooperators (low harvest, share migration)')
        plt.plot(self.stats['steps'], self.stats['conditionals'], 'b-', label='Conditionals (high harvest, share migration)')
        plt.plot(self.stats['steps'], self.stats['defectors'], 'r-', label='Defectors (high harvest, no migration help)')
        plt.title('Agent Population Evolution')
        plt.xlabel('Step')
        plt.ylabel('Number')
        plt.legend()
        plt.grid(True)
        agent_plot_path = os.path.join(results_dir, f"{self.results_prefix}_agents.png")
        plt.savefig(agent_plot_path)
        logger.info(f"Saving agent population plot to: {agent_plot_path}")
        plt.close()

        # Resources evolution
        plt.figure(figsize=(10, 6))
        plt.plot(self.stats['steps'], self.stats['total_resources'], 'k-', label='Total Resources')
        plt.title('Total Resources Evolution')
        plt.xlabel('Step')
        plt.ylabel('Resources')
        plt.legend()
        plt.grid(True)
        resources_plot_path = os.path.join(results_dir, f"{self.results_prefix}_resources.png")
        plt.savefig(resources_plot_path)
        logger.info(f"Saving resources plot to: {resources_plot_path}")
        plt.close()

        # Final populations bar chart
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
        logger.info(f"Saving summary bar chart to: {summary_plot_path}")
        plt.close()

        # Migration statistics
        plt.figure(figsize=(12, 6))
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
        plt.xticks(rotation=45)
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom')
        plt.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        migration_plot_path = os.path.join(results_dir, f"{self.results_prefix}_migrations.png")
        plt.savefig(migration_plot_path)
        logger.info(f"Saving migration statistics plot to: {migration_plot_path}")
        plt.close()

# ---------------- Enhanced Animation ----------------
def animate_simulation(model, steps=1000, steps_per_frame=1, interval=100, show_energy=False):
    """Enhanced animation with better performance but original visual style"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # Initialize visualization
    grid_display = np.zeros((model.width, model.height))
    im = ax1.imshow(grid_display.T, origin='lower', cmap='YlGn', vmin=0, vmax=model.carrying_capacity)
    scatter = ax1.scatter([], [], s=25)
    ax1.set_xlim(-0.5, model.width - 0.5)
    ax1.set_ylim(-0.5, model.height - 0.5)
    ax1.set_title("Step 0")
    fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)

    # Population chart
    ax2.set_title('Agent Population Evolution (Enhanced)')
    ax2.set_xlabel('Step')
    ax2.set_ylabel('Number')
    line_coop, = ax2.plot([], [], 'g-', linewidth=2, label='Cooperators (low harvest, share migration)')
    line_cond, = ax2.plot([], [], 'b-', linewidth=2, label='Conditionals (high harvest, share migration)')
    line_def, = ax2.plot([], [], 'r-', linewidth=2, label='Defectors (high harvest, no migration help)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, steps)
    ax2.set_ylim(0, model.initial_agents * 3)

    colors_map = {"cooperator": "green", "conditional": "blue", "defector": "red"}

    # Energy display
    energy_texts = []
    performance_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes, 
                               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    def update(frame):
        nonlocal energy_texts

        frame_start = time.time()

        # Run simulation steps
        for i in range(steps_per_frame):
            current_step = frame * steps_per_frame + i
            if current_step >= steps:
                ani.event_source.stop()
                model.save_results()
                logger.info(f"Simulation finished. Results saved with prefix: {model.results_prefix}")
                return

            model.step()
            model.collect_stats(current_step)

        # Update resource grid visualization
        grid_display[:] = model.resource_grid
        im.set_data(grid_display.T)

        # Update agent positions
        alive_agents = model.get_alive_agents()
        if alive_agents:
            xs = [a['position'][0] for a in alive_agents]
            ys = [a['position'][1] for a in alive_agents]
            cs = [colors_map[a['strategy']] for a in alive_agents]
            scatter.set_offsets(np.c_[xs, ys])
            scatter.set_color(cs)
            scatter.set_sizes([30] * len(alive_agents))  
        else:
            scatter.set_offsets([])

        # === Energy display: 
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

        # Update population lines
        if model.stats.get('steps'):
            line_coop.set_data(model.stats['steps'], model.stats['cooperators'])
            line_cond.set_data(model.stats['steps'], model.stats['conditionals'])
            line_def.set_data(model.stats['steps'], model.stats['defectors'])

        # Performance info
        current_step = frame * steps_per_frame
        total_agents = len(alive_agents)
        frame_time = time.time() - frame_start

        perf_info = (f"Step: {current_step}\n"
                     f"Agents: {total_agents}\n"
                     f"Frame time: {frame_time:.3f}s\n"
                     f"Loop prevention: {model.loop_prevention_moves}/{model.total_moves}")

        ax1.set_title(f"Enhanced Simulation - Step {current_step}")

        return [scatter, im, line_coop, line_cond, line_def, performance_text] + energy_texts


    total_frames = max(1, steps // steps_per_frame)
    
    ani = animation.FuncAnimation(fig, update, frames=total_frames + 1,
                                  interval=interval, blit=False, repeat=False)

    def on_close(event):
        model.save_results()
        logger.info("Window closed: results saved.")
    
    fig.canvas.mpl_connect('close_event', on_close)
    plt.tight_layout()
    plt.show()
    
    return ani

def run_simulation_with_params():
    """Enhanced parameter selection GUI"""
    global root, entries, show_energy_labels, debug_mode_var
    
    root = tk.Tk()
    root.title("Enhanced Agent-based Model Parameters")
    root.geometry("500x700")
    
    show_energy_labels = tk.BooleanVar(value=True)
    debug_mode_var = tk.BooleanVar(value=True)

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
        "percent_cooperators": 60, "percent_conditionals": 10,
        "patch_width": 4, "gap_size": 20, "carrying_capacity": 10,
        "growth_rate": 0.2, "living_costs": 1, "dispersal_cost": 8,
        "group_dispersal_range": 50, "mutation_rate": 0.0,
        "cost_child": 10, "steps": 1000, "steps_per_frame": 1,
        "random_seed": "", "results_prefix": "enhanced_simulation"
    }

    descriptions = {
        "width": "Grid width (cells)",
        "height": "Grid height (cells)",
        "initial_agents": "Starting number of agents",
        "percent_cooperators": "% Cooperators (low harvest, share cost)",
        "percent_conditionals": "% Conditionals (high harvest, share cost)", 
        "patch_width": "Radius of food patches",
        "gap_size": "Distance between food patches",
        "carrying_capacity": "Max resources per patch",
        "growth_rate": "Resource regrowth rate",
        "living_costs": "Energy cost per step",
        "dispersal_cost": "Cost for crossing gaps",
        "group_dispersal_range": "Range for cost sharing",
        "mutation_rate": "Strategy mutation probability",
        "cost_child": "Energy cost for reproduction",
        "steps": "Total simulation steps",
        "steps_per_frame": "Steps per animation frame",
        "random_seed": "Random seed (empty = random)",
        "results_prefix": "Output file prefix"
    }

    entries = {}
    
    # Create scrollable frame
    canvas = tk.Canvas(root)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Add parameter inputs
    for i, label in enumerate(labels):
        frame = tk.Frame(scrollable_frame)
        frame.pack(fill="x", padx=5, pady=2)
        
        tk.Label(frame, text=f"{label}:", width=20, anchor="w").pack(side="left")
        e = tk.Entry(frame, width=15)
        e.pack(side="left", padx=5)
        e.insert(0, str(defaults[label]))
        entries[label] = e
        
        # Add description
        desc_label = tk.Label(frame, text=descriptions[label], 
                             font=("Arial", 8), fg="gray", anchor="w")
        desc_label.pack(side="left", padx=5)

    # Options frame
    options_frame = tk.Frame(scrollable_frame)
    options_frame.pack(fill="x", padx=5, pady=10)
    
    tk.Checkbutton(options_frame, text="Show agent energy", 
                  variable=show_energy_labels).pack(anchor="w")
    tk.Checkbutton(options_frame, text="Debug mode (detailed logging)", 
                  variable=debug_mode_var).pack(anchor="w")

    def start_simulation():
        try:
            # Separate model parameters from animation parameters
            model_params = {}
            animation_params = {}
            
            for key in labels:
                value = entries[key].get().strip()
                
                # Animation-only parameters
                if key in ["steps", "steps_per_frame"]:
                    if key == "steps":
                        animation_params['steps'] = int(value)
                    elif key == "steps_per_frame":
                        animation_params['steps_per_frame'] = int(value)
                    continue
                
                # Model parameters
                if key in ["width", "height", "initial_agents", "patch_width", "gap_size"]:
                    model_params[key] = int(value)
                elif key == "results_prefix":
                    model_params[key] = value
                elif key == "random_seed":
                    # Handle seed separately
                    model_params['random_seed'] = int(value) if value != "" else None
                else:
                    model_params[key] = float(value)
            
            # Add debug mode
            model_params['debug_mode'] = debug_mode_var.get()
            
            # Validation
            if model_params['percent_cooperators'] + model_params['percent_conditionals'] > 100:
                raise ValueError("Cooperators + Conditionals cannot exceed 100%")
            
            if model_params['width'] <= 0 or model_params['height'] <= 0:
                raise ValueError("Width and height must be positive")
            
            if animation_params['steps'] <= 0:
                raise ValueError("Steps must be positive")
                
            if animation_params['steps_per_frame'] <= 0:
                raise ValueError("Steps per frame must be positive")

            root.destroy()
            
            logger.info(f"Starting enhanced simulation with parameters: {model_params}")
            logger.info(f"Animation settings: {animation_params}")
            
            model = AgentModel(**model_params)
            
            animate_simulation(
                model,
                steps=animation_params['steps'],
                steps_per_frame=animation_params['steps_per_frame'],
                interval=50,  # Faster animation
                show_energy=show_energy_labels.get()
            )
            
        except Exception as e:
            messagebox.showerror("Input Error", f"Error: {str(e)}")
            logger.error(f"Parameter error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

    # Control buttons
    button_frame = tk.Frame(scrollable_frame)
    button_frame.pack(fill="x", padx=5, pady=10)
    
    tk.Button(button_frame, text="Start Enhanced Simulation", 
              command=start_simulation, bg="lightgreen", font=("Arial", 12, "bold")).pack(pady=5)
    
    tk.Button(button_frame, text="Reset to Defaults", 
              command=lambda: reset_defaults()).pack(pady=2)

    def reset_defaults():
        for label, entry in entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(defaults[label]))

    # Pack scrollable elements
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    root.mainloop()

if __name__ == "__main__":
    logger.info("Starting Enhanced Agent-Based Model")
    run_simulation_with_params()