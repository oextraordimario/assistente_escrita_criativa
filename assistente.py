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
        """Calculate optimal positions for nodes"""
        self.pos = {}
        
        # Central node at origin
        self.pos[central_node] = (0, 0)
        
        # Get categories (nodes connected to central)
        categories = list(self.G.neighbors(central_node))
        num_categories = len(categories)
        
        if num_categories == 0:
            return
        
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
                        leaf_angle = angle + angular_span * (j - (num_leaves - 1) / 2) / (num_leaves - 1)
                    
                    leaf_x = x + leaf_radius * math.cos(leaf_angle)
                    leaf_y = y + leaf_radius * math.sin(leaf_angle)
                    self.pos[leaf] = (leaf_x, leaf_y)
    
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
        
        # Draw nodes
        for node, (x, y) in self.pos.items():
            node_data = self.G.nodes[node]
            node_type = node_data.get('node_type', 'leaf')
            
            # Set node properties based on type
            if node_type == 'central':
                size = 1.5
                color = '#2C3E50'
                text_color = 'white'
                font_size = 14
                font_weight = 'bold'
            elif node_type == 'category':
                size = 1.0
                color_index = node_data.get('color_index', 0)
                color = self.colors[color_index]
                text_color = 'white'
                font_size = 11
                font_weight = 'bold'
            else:  # leaf
                size = 0.7
                color_index = node_data.get('color_index', 0)
                color = self.colors[color_index]
                text_color = 'white'
                font_size = 9
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
            self.ax.add_patch(bbox)
            
            # Add text
            self.ax.text(x, y, node, ha='center', va='center',
                        fontsize=font_size, fontweight=font_weight,
                        color=text_color, zorder=3,
                        bbox=dict(boxstyle="round,pad=0.05", 
                                facecolor='none', edgecolor='none'))
        
        # Set title
        self.ax.set_title(f'Mapa Mental: {central_node}', fontsize=18, fontweight='bold', pad=20)
        
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