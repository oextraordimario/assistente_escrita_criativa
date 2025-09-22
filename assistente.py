import json
import os
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import FancyBboxPatch
import tkinter as tk
from tkinter import filedialog
import math

class MindMapVisualizer:
    def __init__(self):
        self.G = nx.Graph()
        self.pos = {}
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        
    def load_json(self, filepath=None):
        """Load JSON file, either from filepath or file dialog"""
        if filepath is None:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            filepath = filedialog.askopenfilename(
                title="Select JSON file",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            root.destroy()
            
        if not filepath:
            return None
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data, os.path.splitext(os.path.basename(filepath))[0]
        except Exception as e:
            print(f"Error loading file: {e}")
            return None
    
    def build_graph(self, data, central_node):
        """Build the graph structure from JSON data"""
        self.G.clear()
        
        # Add central node
        self.G.add_node(central_node, node_type='central')
        
        # Add category nodes and leaf nodes
        for i, (category, items) in enumerate(data.items()):
            # Add category node
            self.G.add_node(category, node_type='category', color_index=i % len(self.colors))
            self.G.add_edge(central_node, category)
            
            # Add leaf nodes
            if isinstance(items, list):
                for item in items:
                    self.G.add_node(item, node_type='leaf', color_index=i % len(self.colors))
                    self.G.add_edge(category, item)
            else:
                # Handle non-list values
                self.G.add_node(str(items), node_type='leaf', color_index=i % len(self.colors))
                self.G.add_edge(category, str(items))
    
    def calculate_positions(self, central_node):
        """Calculate optimal positions for nodes"""
        self.pos = {}
        
        # Central node at origin
        self.pos[central_node] = (0, 0)
        
        # Get categories (nodes connected to central)
        categories = list(self.G.neighbors(central_node))
        num_categories = len(categories)
        
        # Position categories in a circle around central node
        category_radius = 3
        for i, category in enumerate(categories):
            angle = 2 * math.pi * i / num_categories
            x = category_radius * math.cos(angle)
            y = category_radius * math.sin(angle)
            self.pos[category] = (x, y)
            
            # Position leaf nodes around their category
            leaves = [n for n in self.G.neighbors(category) if n != central_node]
            num_leaves = len(leaves)
            
            if num_leaves > 0:
                leaf_radius = 2
                # Calculate the angular span for this category's leaves
                angular_span = math.pi / 3  # 60 degrees total span
                
                for j, leaf in enumerate(leaves):
                    if num_leaves == 1:
                        leaf_angle = angle
                    else:
                        # Distribute leaves within the angular span
                        leaf_angle = angle + angular_span * (j - (num_leaves - 1) / 2) / (num_leaves - 1) if num_leaves > 1 else angle
                    
                    leaf_x = x + leaf_radius * math.cos(leaf_angle)
                    leaf_y = y + leaf_radius * math.sin(leaf_angle)
                    self.pos[leaf] = (leaf_x, leaf_y)
    
    def visualize(self, data, central_node, save_path=None):
        """Create and display the mind map visualization"""
        self.build_graph(data, central_node)
        self.calculate_positions(central_node)
        
        # Create figure and axis
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Draw edges first (so they appear behind nodes)
        for edge in self.G.edges():
            x_values = [self.pos[edge[0]][0], self.pos[edge[1]][0]]
            y_values = [self.pos[edge[0]][1], self.pos[edge[1]][1]]
            ax.plot(x_values, y_values, 'gray', alpha=0.6, linewidth=2, zorder=1)
        
        # Draw nodes
        for node, (x, y) in self.pos.items():
            node_data = self.G.nodes[node]
            node_type = node_data.get('node_type', 'leaf')
            
            # Set node properties based on type
            if node_type == 'central':
                size = 1.5
                color = '#2C3E50'
                text_color = 'white'
                font_size = 16
                font_weight = 'bold'
            elif node_type == 'category':
                size = 1.0
                color_index = node_data.get('color_index', 0)
                color = self.colors[color_index]
                text_color = 'white'
                font_size = 12
                font_weight = 'bold'
            else:  # leaf
                size = 0.7
                color_index = node_data.get('color_index', 0)
                color = self.colors[color_index]
                text_color = 'white'
                font_size = 10
                font_weight = 'normal'
            
            # Create node background
            bbox = FancyBboxPatch(
                (x - size/2, y - size/4),
                size, size/2,
                boxstyle="round,pad=0.1",
                facecolor=color,
                edgecolor='white',
                linewidth=2,
                zorder=2
            )
            ax.add_patch(bbox)
            
            # Add text
            ax.text(x, y, node, ha='center', va='center',
                   fontsize=font_size, fontweight=font_weight,
                   color=text_color, zorder=3,
                   bbox=dict(boxstyle="round,pad=0.05", 
                           facecolor='none', edgecolor='none'))
        
        # Set title
        ax.set_title(f'Mind Map: {central_node}', fontsize=20, fontweight='bold', pad=20)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save if path provided
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"Mind map saved to: {save_path}")
        
        # Display
        plt.show()
    
    def run(self, json_file=None):
        """Main method to run the visualizer"""
        # Load JSON data
        result = self.load_json(json_file)
        if result is None:
            print("No file selected or error loading file.")
            return
        
        data, central_node = result
        
        print(f"Loaded: {central_node}")
        print(f"Categories: {list(data.keys())}")
        
        # Create visualization
        self.visualize(data, central_node)

# Example usage and testing
def main():
    # Create visualizer instance
    visualizer = MindMapVisualizer()
    
    # Example: Create test data matching your example
    test_data = {
        "Natureza": [
            "folhagem", "raízes", "copa", 
            "tronco", "frutos", "flores"
        ],
        "Ciclo da Vida": [
            "crescimento", "sazonalidade", "transformação", 
            "regeneração", "entalhadura"
        ]
    }
    
    # You can test with the example data
    #print("Testing with example data...")
    #visualizer.visualize(test_data, "Árvore")
    
    # Or run with file dialog to select your own JSON file
    #print("\nTo load your own JSON file, uncomment the next line:")
    visualizer.run()

if __name__ == "__main__":
    main()