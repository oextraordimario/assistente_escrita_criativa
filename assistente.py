import json
import os
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import FancyBboxPatch
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import math
from datetime import datetime
import threading
import dspy
from dotenv import load_dotenv
import glob
import textwrap

class MindMapVisualizer:
    def __init__(self):
        self.G = nx.Graph()
        self.pos = {}
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        
        # Create directories if they don't exist
        os.makedirs("prompts", exist_ok=True)
        os.makedirs("json", exist_ok=True)
        
        # Initialize DSPy
        self.setup_dspy()
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Mind Map Visualizer with LLM")
        self.root.state('zoomed')  # Full screen on Windows
        # For other OS, use: self.root.attributes('-zoomed', True)  # Linux
        # For MacOS, use: self.root.attributes('-fullscreen', True)
        
        self.setup_ui()
        
    def setup_dspy(self):
        """Initialize DSPy with API keys"""
        try:
            load_dotenv("auth.env")
            self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not self.openai_api_key and not self.anthropic_api_key:
                messagebox.showwarning("API Keys", "Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables")
                
        except Exception as e:
            messagebox.showerror("DSPy Setup Error", f"Error setting up DSPy: {e}")
    
    def setup_ui(self):
        """Create the main UI with sidebar and canvas"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left sidebar
        self.setup_sidebar(main_frame)
        
        # Right canvas area
        self.setup_canvas_area(main_frame)
    
    def setup_sidebar(self, parent):
        """Create the left sidebar with controls"""
        sidebar_frame = ttk.Frame(parent, width=350)
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar_frame.pack_propagate(False)
        
        # Title
        title_label = ttk.Label(sidebar_frame, text="Mind Map Generator", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Main word input
        ttk.Label(sidebar_frame, text="Palavra Principal:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.main_word_entry = ttk.Entry(sidebar_frame, font=('Arial', 12))
        self.main_word_entry.pack(fill=tk.X, pady=(5, 15))
        
        # Prompt input
        ttk.Label(sidebar_frame, text="Prompt:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.prompt_text = scrolledtext.ScrolledText(sidebar_frame, height=15, font=('Arial', 10))
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        # Model selection
        ttk.Label(sidebar_frame, text="Modelo LLM:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.model_var = tk.StringVar()
        model_frame = ttk.Frame(sidebar_frame)
        model_frame.pack(fill=tk.X, pady=(5, 15))
        
        self.model_dropdown = ttk.Combobox(model_frame, textvariable=self.model_var, 
                                          state="readonly", font=('Arial', 10))
        self.model_dropdown['values'] = [
            'openai/gpt-4o',
            'openai/gpt-4o-mini',
            'openai/gpt-3.5-turbo',
            'anthropic/claude-3-5-sonnet-20241022',
            'anthropic/claude-3-5-haiku-20241022',
            'anthropic/claude-3-opus-20240229'
        ]
        self.model_dropdown.set('openai/gpt-4o-mini')
        self.model_dropdown.pack(fill=tk.X)
        
        # Send button
        self.send_button = ttk.Button(sidebar_frame, text="Enviar", 
                                     command=self.on_send_click, 
                                     style='Accent.TButton')
        self.send_button.pack(pady=10, fill=tk.X)
        
        # Progress bar
        self.progress = ttk.Progressbar(sidebar_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(sidebar_frame, text="Pronto", foreground='green')
        self.status_label.pack()
        
        # Load JSON button
        ttk.Button(sidebar_frame, text="Carregar JSON", 
                  command=self.load_json_file).pack(pady=(20, 5), fill=tk.X)
        
        # Load latest prompt after all UI elements are created
        self.load_latest_prompt()
    
    def setup_canvas_area(self, parent):
        """Create the right canvas area for mind map display"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(1, 1, figsize=(12, 8))
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initial message
        self.ax.text(0.5, 0.5, 'Carregue um JSON ou gere um novo mapa mental', 
                    transform=self.ax.transAxes, ha='center', va='center',
                    fontsize=16, color='gray')
        self.canvas.draw()
    
    def load_latest_prompt(self):
        """Load the latest .md file from prompts folder into the prompt text box"""
        try:
            # Get all .md files in prompts folder
            md_files = glob.glob("prompts/*.md")
            
            if md_files:
                # Sort by modification time (newest first)
                latest_file = max(md_files, key=os.path.getmtime)
                
                # Read and load the content
                with open(latest_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Clear and insert content into text box
                self.prompt_text.delete("1.0", tk.END)
                self.prompt_text.insert("1.0", content)
                
                # Update status
                filename = os.path.basename(latest_file)
                self.status_label.config(text=f"Prompt carregado: {filename}", foreground='blue')
            else:
                # No .md files found
                self.status_label.config(text="Nenhum prompt encontrado", foreground='gray')
                
        except Exception as e:
            print(f"Error loading latest prompt: {e}")
            self.status_label.config(text="Erro ao carregar prompt", foreground='red')
    
    def on_send_click(self):
        """Handle send button click"""
        main_word = self.main_word_entry.get().strip()
        prompt_content = self.prompt_text.get("1.0", tk.END).strip()
        
        if not main_word:
            messagebox.showerror("Erro", "Por favor, insira uma palavra principal")
            return
            
        if not prompt_content:
            messagebox.showerror("Erro", "Por favor, insira um prompt")
            return
        
        # Disable button and start progress
        self.send_button.config(state='disabled')
        self.progress.start()
        self.status_label.config(text="Gerando...", foreground='orange')
        
        # Run in separate thread to avoid blocking UI
        thread = threading.Thread(target=self.generate_mindmap, 
                                 args=(main_word, prompt_content))
        thread.start()
    
    def generate_mindmap(self, main_word, prompt_content):
        """Generate mind map using LLM"""
        try:
            # Save prompt as MD file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prompt_filename = f"prompts/{timestamp}.md"
            
            with open(prompt_filename, "w", encoding="utf-8") as f:
                f.write(prompt_content)
            
            # Configure DSPy model
            model_name = self.model_var.get()
            lm = dspy.LM(
                model_name,
                model_type="responses",
                temperature=1.0,
                max_tokens=16000,
            )
            dspy.settings.configure(lm=lm)
            
            # Make LLM call
            with open(prompt_filename, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            
            response = lm(messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": main_word}
            ])
            
            response_text = "\n\n".join(response)
            
            # Try to extract JSON from response
            json_data = self.extract_json_from_response(response_text)
            
            if json_data:
                # Save JSON file
                json_filename = f"json/{main_word}.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                # Update UI in main thread
                self.root.after(0, self.update_ui_success, json_data, main_word)
            else:
                self.root.after(0, self.update_ui_error, "Não foi possível extrair JSON válido da resposta")
                
        except Exception as e:
            self.root.after(0, self.update_ui_error, str(e))
    
    def extract_json_from_response(self, response_text):
        """Extract JSON from LLM response"""
        try:
            # Try to find JSON in the response
            import re
            
            # Look for JSON blocks
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, response_text, re.DOTALL)
            
            if match:
                json_str = match.group(1)
            else:
                # Try to find JSON without code blocks
                json_pattern = r'\{.*\}'
                match = re.search(json_pattern, response_text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    # Assume entire response is JSON
                    json_str = response_text
            
            return json.loads(json_str)
            
        except json.JSONDecodeError:
            return None
    
    def update_ui_success(self, json_data, main_word):
        """Update UI after successful generation"""
        self.progress.stop()
        self.send_button.config(state='normal')
        self.status_label.config(text="Concluído!", foreground='green')
        
        # Visualize the mind map
        self.visualize_mindmap(json_data, main_word)
    
    def update_ui_error(self, error_message):
        """Update UI after error"""
        self.progress.stop()
        self.send_button.config(state='normal')
        self.status_label.config(text="Erro", foreground='red')
        messagebox.showerror("Erro", f"Erro ao gerar mapa mental: {error_message}")
    
    def load_json_file(self):
        """Load JSON file from file dialog"""
        filepath = filedialog.askopenfilename(
            title="Selecionar arquivo JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                filename = os.path.splitext(os.path.basename(filepath))[0]
                self.visualize_mindmap(data, filename)
                self.status_label.config(text="JSON carregado", foreground='green')
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar JSON: {e}")
    
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
        """Calculate optimal positions for nodes with proper spacing"""
        self.pos = {}
        
        # Central node at origin
        self.pos[central_node] = (0, 0)
        
        # Get categories (nodes connected to central)
        categories = list(self.G.neighbors(central_node))
        num_categories = len(categories)
        
        if num_categories == 0:
            return
        
        # Position categories in a circle around central node with increased radius for spacing
        category_radius = 4  # Increased from 3 to 4 for more spacing
        for i, category in enumerate(categories):
            angle = 2 * math.pi * i / num_categories
            x = category_radius * math.cos(angle)
            y = category_radius * math.sin(angle)
            self.pos[category] = (x, y)
            
            # Position leaf nodes around their category
            leaves = [n for n in self.G.neighbors(category) if n != central_node]
            num_leaves = len(leaves)
            
            if num_leaves > 0:
                leaf_radius = 2.5  # Increased from 2 to 2.5 for more spacing
                # Calculate the angular span for this category's leaves
                angular_span = math.pi / 2.5  # Reduced from pi/3 to pi/2.5 for wider spread
                
                for j, leaf in enumerate(leaves):
                    if num_leaves == 1:
                        leaf_angle = angle
                    else:
                        # Distribute leaves within the angular span
                        leaf_angle = angle + angular_span * (j - (num_leaves - 1) / 2) / (num_leaves - 1)
                    
                    leaf_x = x + leaf_radius * math.cos(leaf_angle)
                    leaf_y = y + leaf_radius * math.sin(leaf_angle)
                    self.pos[leaf] = (leaf_x, leaf_y)
    
    def wrap_text(self, text, max_chars_per_line):
        """Wrap text to fit within specified character limit per line"""
        return textwrap.fill(text, width=max_chars_per_line)
    
    def get_text_dimensions(self, text, font_size):
        """Estimate text dimensions for proper box sizing"""
        lines = text.split('\n')
        max_chars = max(len(line) for line in lines) if lines else 0
        num_lines = len(lines)
        
        # Rough estimation: each character is about 0.6 * font_size wide
        # each line is about 1.2 * font_size tall
        width = max_chars * font_size * 0.06
        height = num_lines * font_size * 0.12
        
        return width, height
    
    def visualize_mindmap(self, data, central_node):
        """Create and display the mind map visualization"""
        self.build_graph(data, central_node)
        self.calculate_positions(central_node)
        
        # Clear previous plot
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        
        if not self.pos:
            self.ax.text(0.5, 0.5, 'Dados JSON inválidos', 
                        transform=self.ax.transAxes, ha='center', va='center',
                        fontsize=16, color='red')
            self.canvas.draw()
            return
        
        # Draw edges first (so they appear behind nodes)
        for edge in self.G.edges():
            x_values = [self.pos[edge[0]][0], self.pos[edge[1]][0]]
            y_values = [self.pos[edge[0]][1], self.pos[edge[1]][1]]
            self.ax.plot(x_values, y_values, 'gray', alpha=0.6, linewidth=2, zorder=1)
        
        # Draw nodes with proper text wrapping and sizing
        for node, (x, y) in self.pos.items():
            node_data = self.G.nodes[node]
            node_type = node_data.get('node_type', 'leaf')
            
            # Set node properties based on type and wrap text
            if node_type == 'central':
                wrapped_text = self.wrap_text(node, 15)  # 15 chars per line for central
                base_width, base_height = 2.0, 0.8
                color = '#2C3E50'
                text_color = 'white'
                font_size = 14
                font_weight = 'bold'
            elif node_type == 'category':
                wrapped_text = self.wrap_text(node, 12)  # 12 chars per line for categories
                base_width, base_height = 1.6, 0.6
                color_index = node_data.get('color_index', 0)
                color = self.colors[color_index]
                text_color = 'white'
                font_size = 11
                font_weight = 'bold'
            else:  # leaf
                wrapped_text = self.wrap_text(node, 10)  # 10 chars per line for leaves
                base_width, base_height = 1.2, 0.5
                color_index = node_data.get('color_index', 0)
                color = self.colors[color_index]
                text_color = 'white'
                font_size = 9
                font_weight = 'normal'
            
            # Calculate actual dimensions based on wrapped text
            text_width, text_height = self.get_text_dimensions(wrapped_text, font_size)
            
            # Use the larger of base size or text size, with some padding
            box_width = max(base_width, text_width + 0.4)
            box_height = max(base_height, text_height + 0.3)
            
            # Create node background
            bbox = FancyBboxPatch(
                (x - box_width/2, y - box_height/2),
                box_width, box_height,
                boxstyle="round,pad=0.1",
                facecolor=color,
                edgecolor='white',
                linewidth=2,
                zorder=2
            )
            self.ax.add_patch(bbox)
            
            # Add wrapped text
            self.ax.text(x, y, wrapped_text, ha='center', va='center',
                        fontsize=font_size, fontweight=font_weight,
                        color=text_color, zorder=3,
                        bbox=dict(boxstyle="round,pad=0.05", 
                                facecolor='none', edgecolor='none'))
        
        # Set title
        self.ax.set_title(f'Mapa Mental: {central_node}', fontsize=18, fontweight='bold', pad=20)
        
        # Adjust plot limits to ensure all nodes are visible with padding
        if self.pos:
            x_coords = [pos[0] for pos in self.pos.values()]
            y_coords = [pos[1] for pos in self.pos.values()]
            
            x_margin = (max(x_coords) - min(x_coords)) * 0.2 + 2
            y_margin = (max(y_coords) - min(y_coords)) * 0.2 + 2
            
            self.ax.set_xlim(min(x_coords) - x_margin, max(x_coords) + x_margin)
            self.ax.set_ylim(min(y_coords) - y_margin, max(y_coords) + y_margin)
        
        # Refresh canvas
        self.canvas.draw()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main function to run the application"""
    app = MindMapVisualizer()
    app.run()

if __name__ == "__main__":
    main()