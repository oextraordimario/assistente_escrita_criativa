import json
import os
import sys
import math
from datetime import datetime
import threading
import dspy
from dotenv import load_dotenv
import glob
import textwrap
import re

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                               QVBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                               QLabel, QComboBox, QProgressBar, QFileDialog, 
                               QMessageBox, QGraphicsView, QGraphicsScene, 
                               QGraphicsItem, QGraphicsTextItem, QScrollArea,
                               QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath

class MindMapNode(QGraphicsItem):
    def __init__(self, text, node_type, color_index=0):
        super().__init__()
        self.text = text
        self.node_type = node_type
        self.color_index = color_index
        self.wrapped_text = ""
        self.is_selected = False
        
        # Colors for different categories
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        
        # Make item draggable and selectable
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # Set properties based on node type
        self.setup_node_properties()
        
    def setup_node_properties(self):
        """Set node properties based on type"""
        if self.node_type == 'central':
            self.wrapped_text = self.wrap_text(self.text, 15)
            self.base_width, self.base_height = 200, 80
            self.color = QColor('#2C3E50')
            self.text_color = QColor('white')
            self.font_size = 14
            self.font_weight = True
        elif self.node_type == 'category':
            self.wrapped_text = self.wrap_text(self.text, 12)
            self.base_width, self.base_height = 160, 60
            self.color = QColor(self.colors[self.color_index])
            self.text_color = QColor('white')
            self.font_size = 11
            self.font_weight = True
        else:  # leaf
            self.wrapped_text = self.wrap_text(self.text, 10)
            self.base_width, self.base_height = 120, 50
            self.color = QColor(self.colors[self.color_index])
            self.text_color = QColor('white')
            self.font_size = 9
            self.font_weight = False
            
        # Calculate actual dimensions based on text
        self.calculate_dimensions()
        
    def wrap_text(self, text, max_chars_per_line):
        """Wrap text to fit within specified character limit per line"""
        return textwrap.fill(text, width=max_chars_per_line)
        
    def calculate_dimensions(self):
        """Calculate node dimensions based on wrapped text"""
        lines = self.wrapped_text.split('\n')
        max_chars = max(len(line) for line in lines) if lines else 0
        num_lines = len(lines)
        
        # Estimate dimensions
        text_width = max_chars * self.font_size * 0.6
        text_height = num_lines * self.font_size * 1.2
        
        # Use larger of base size or text size, with padding
        self.width = max(self.base_width, text_width + 40)
        self.height = max(self.base_height, text_height + 30)
        
    def boundingRect(self):
        """Return bounding rectangle for the item"""
        return QRectF(-self.width/2, -self.height/2, self.width, self.height)
        
    def paint(self, painter, option, widget):
        """Paint the node"""
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Selection highlight
        if self.isSelected():
            painter.setPen(QPen(QColor('#FFD700'), 3))  # Gold selection border
            painter.setBrush(QBrush(self.color))
        else:
            painter.setPen(QPen(QColor('white'), 2))
            painter.setBrush(QBrush(self.color))
            
        # Draw rounded rectangle
        rect = self.boundingRect()
        painter.drawRoundedRect(rect, 10, 10)
        
        # Draw text
        painter.setPen(QPen(self.text_color))
        font = QFont()
        font.setPointSize(self.font_size)
        font.setBold(self.font_weight)
        painter.setFont(font)
        
        painter.drawText(rect, Qt.AlignCenter, self.wrapped_text)
        
    def mousePressEvent(self, event):
        """Handle mouse press for selection"""
        super().mousePressEvent(event)
        # Emit selection change if needed
        if self.scene():
            self.scene().update_selection()

class ConnectionLine(QGraphicsItem):
    def __init__(self, start_node, end_node):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.setZValue(-1)  # Draw behind nodes
        
    def boundingRect(self):
        """Return bounding rectangle for the line"""
        start_pos = self.start_node.pos()
        end_pos = self.end_node.pos()
        
        return QRectF(
            min(start_pos.x(), end_pos.x()) - 10,
            min(start_pos.y(), end_pos.y()) - 10,
            abs(end_pos.x() - start_pos.x()) + 20,
            abs(end_pos.y() - start_pos.y()) + 20
        )
        
    def paint(self, painter, option, widget):
        """Paint the connection line"""
        painter.setRenderHint(QPainter.Antialiasing)
        
        start_pos = self.start_node.pos()
        end_pos = self.end_node.pos()
        
        painter.setPen(QPen(QColor('gray'), 2))
        painter.drawLine(start_pos, end_pos)

class MindMapScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.connections = []
        self.setSceneRect(-2000, -2000, 4000, 4000)
        
    def clear_mindmap(self):
        """Clear all nodes and connections"""
        self.clear()
        self.nodes = {}
        self.connections = []
        
    def add_mindmap_node(self, node_id, text, node_type, color_index=0, position=None):
        """Add a node to the mind map"""
        node = MindMapNode(text, node_type, color_index)
        if position:
            node.setPos(position)
        self.addItem(node)
        self.nodes[node_id] = node
        return node
        
    def add_connection(self, start_id, end_id):
        """Add a connection between two nodes"""
        if start_id in self.nodes and end_id in self.nodes:
            connection = ConnectionLine(self.nodes[start_id], self.nodes[end_id])
            self.addItem(connection)
            self.connections.append(connection)
            
    def update_selection(self):
        """Update when selection changes"""
        selected_items = self.selectedItems()
        # You can add custom selection handling here later
        pass

class LLMWorker(QThread):
    finished = Signal(dict, str)  # json_data, main_word
    error = Signal(str)
    
    def __init__(self, main_word, prompt_content, model_name):
        super().__init__()
        self.main_word = main_word
        self.prompt_content = prompt_content
        self.model_name = model_name
        
    def run(self):
        try:
            # Save prompt as MD file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prompt_filename = f"prompts/{timestamp}.md"
            
            with open(prompt_filename, "w", encoding="utf-8") as f:
                f.write(self.prompt_content)
            
            # Configure DSPy model
            lm = dspy.LM(
                self.model_name,
                model_type="responses",
                temperature=1.0,
                max_tokens=16000,
            )
            dspy.settings.configure(lm=lm)
            
            # Make LLM call
            response = lm(messages=[
                {"role": "system", "content": self.prompt_content},
                {"role": "user", "content": self.main_word}
            ])
            
            response_text = "\n\n".join(response)
            
            # Extract JSON from response
            json_data = self.extract_json_from_response(response_text)
            
            if json_data:
                # Save JSON file
                json_filename = f"json/{self.main_word}.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                self.finished.emit(json_data, self.main_word)
            else:
                self.error.emit("Não foi possível extrair JSON válido da resposta")
                
        except Exception as e:
            self.error.emit(str(e))
            
    def extract_json_from_response(self, response_text):
        """Extract JSON from LLM response"""
        try:
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

class MindMapVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create directories if they don't exist
        os.makedirs("prompts", exist_ok=True)
        os.makedirs("json", exist_ok=True)
        
        # Initialize DSPy
        self.setup_dspy()
        
        # Setup UI
        self.setup_ui()
        
        # Load latest prompt
        self.load_latest_prompt()
        
    def setup_dspy(self):
        """Initialize DSPy with API keys"""
        try:
            load_dotenv("auth.env")
            self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not self.openai_api_key and not self.anthropic_api_key:
                QMessageBox.warning(self, "API Keys", "Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables")
                
        except Exception as e:
            QMessageBox.critical(self, "DSPy Setup Error", f"Error setting up DSPy: {e}")
    
    def setup_ui(self):
        """Create the main UI"""
        self.setWindowTitle("Mind Map Visualizer with LLM")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left sidebar
        self.setup_sidebar(main_layout)
        
        # Right mind map area
        self.setup_mindmap_area(main_layout)
        
    def setup_sidebar(self, main_layout):
        """Create the left sidebar"""
        sidebar_frame = QFrame()
        sidebar_frame.setFrameStyle(QFrame.StyledPanel)
        sidebar_frame.setFixedWidth(350)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        
        # Title
        title_label = QLabel("Mind Map Generator")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        sidebar_layout.addWidget(title_label)
        
        # Main word input
        sidebar_layout.addWidget(QLabel("Palavra Principal:"))
        self.main_word_entry = QLineEdit()
        self.main_word_entry.setStyleSheet("font-size: 12px; padding: 5px;")
        sidebar_layout.addWidget(self.main_word_entry)
        
        # Prompt input
        sidebar_layout.addWidget(QLabel("Prompt:"))
        self.prompt_text = QTextEdit()
        self.prompt_text.setStyleSheet("font-size: 10px;")
        sidebar_layout.addWidget(self.prompt_text)
        
        # Model selection
        sidebar_layout.addWidget(QLabel("Modelo LLM:"))
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems([
            'openai/gpt-4o',
            'openai/gpt-4o-mini',
            'openai/gpt-3.5-turbo',
            'anthropic/claude-3-5-sonnet-20241022',
            'anthropic/claude-3-5-haiku-20241022',
            'anthropic/claude-3-opus-20240229'
        ])
        self.model_dropdown.setCurrentText('openai/gpt-4o-mini')
        sidebar_layout.addWidget(self.model_dropdown)
        
        # Send button
        self.send_button = QPushButton("Enviar")
        self.send_button.setStyleSheet("font-weight: bold; padding: 10px;")
        self.send_button.clicked.connect(self.on_send_click)
        sidebar_layout.addWidget(self.send_button)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        sidebar_layout.addWidget(self.progress)
        
        # Status label
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("color: green; margin: 5px;")
        sidebar_layout.addWidget(self.status_label)
        
        # Load JSON button
        load_button = QPushButton("Carregar JSON")
        load_button.clicked.connect(self.load_json_file)
        sidebar_layout.addWidget(load_button)
        
        # Selected nodes info (for future use)
        sidebar_layout.addWidget(QLabel("Nodes Selecionados:"))
        self.selection_info = QLabel("Nenhum")
        self.selection_info.setStyleSheet("color: gray; font-style: italic;")
        sidebar_layout.addWidget(self.selection_info)
        
        main_layout.addWidget(sidebar_frame)
        
    def setup_mindmap_area(self, main_layout):
        """Create the right mind map area"""
        # Create graphics view and scene
        self.scene = MindMapScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        
        # Enable zooming with mouse wheel
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        main_layout.addWidget(self.view)
        
        # Initial message
        self.show_initial_message()
        
    def show_initial_message(self):
        """Show initial message in the scene"""
        self.scene.clear_mindmap()
        text_item = self.scene.addText("Carregue um JSON ou gere um novo mapa mental", 
                                      QFont("Arial", 16))
        text_item.setDefaultTextColor(QColor('gray'))
        text_item.setPos(-200, -20)
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        if event.modifiers() == Qt.ControlModifier:
            # Zoom with Ctrl + mouse wheel
            zoom_factor = 1.15
            if event.angleDelta().y() > 0:
                self.view.scale(zoom_factor, zoom_factor)
            else:
                self.view.scale(1/zoom_factor, 1/zoom_factor)
            event.accept()
        else:
            super().wheelEvent(event)
    
    def load_latest_prompt(self):
        """Load the latest .md file from prompts folder"""
        try:
            md_files = glob.glob("prompts/*.md")
            
            if md_files:
                latest_file = max(md_files, key=os.path.getmtime)
                
                with open(latest_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                self.prompt_text.setText(content)
                
                filename = os.path.basename(latest_file)
                self.status_label.setText(f"Prompt carregado: {filename}")
                self.status_label.setStyleSheet("color: blue; margin: 5px;")
            else:
                self.status_label.setText("Nenhum prompt encontrado")
                self.status_label.setStyleSheet("color: gray; margin: 5px;")
                
        except Exception as e:
            print(f"Error loading latest prompt: {e}")
            self.status_label.setText("Erro ao carregar prompt")
            self.status_label.setStyleSheet("color: red; margin: 5px;")
    
    def on_send_click(self):
        """Handle send button click"""
        main_word = self.main_word_entry.text().strip()
        prompt_content = self.prompt_text.toPlainText().strip()
        
        if not main_word:
            QMessageBox.warning(self, "Erro", "Por favor, insira uma palavra principal")
            return
            
        if not prompt_content:
            QMessageBox.warning(self, "Erro", "Por favor, insira um prompt")
            return
        
        # Disable button and start progress
        self.send_button.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("Gerando...")
        self.status_label.setStyleSheet("color: orange; margin: 5px;")
        
        # Start worker thread
        self.worker = LLMWorker(main_word, prompt_content, self.model_dropdown.currentText())
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()
    
    def on_generation_finished(self, json_data, main_word):
        """Handle successful generation"""
        self.send_button.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText("Concluído!")
        self.status_label.setStyleSheet("color: green; margin: 5px;")
        
        # Visualize the mind map
        self.visualize_mindmap(json_data, main_word)
    
    def on_generation_error(self, error_message):
        """Handle generation error"""
        self.send_button.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText("Erro")
        self.status_label.setStyleSheet("color: red; margin: 5px;")
        QMessageBox.critical(self, "Erro", f"Erro ao gerar mapa mental: {error_message}")
    
    def load_json_file(self):
        """Load JSON file from file dialog"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo JSON", "", "JSON files (*.json);;All files (*.*)"
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                filename = os.path.splitext(os.path.basename(filepath))[0]
                self.visualize_mindmap(data, filename)
                self.status_label.setText("JSON carregado")
                self.status_label.setStyleSheet("color: green; margin: 5px;")
                
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao carregar JSON: {e}")
    
    def visualize_mindmap(self, data, central_node):
        """Create and display the interactive mind map"""
        self.scene.clear_mindmap()
        
        # Add central node
        central_pos = QPointF(0, 0)
        self.scene.add_mindmap_node(central_node, central_node, 'central', 0, central_pos)
        
        # Position categories in circle around central node
        categories = list(data.keys())
        num_categories = len(categories)
        category_radius = 300
        
        for i, category in enumerate(categories):
            angle = 2 * math.pi * i / num_categories
            x = category_radius * math.cos(angle)
            y = category_radius * math.sin(angle)
            category_pos = QPointF(x, y)
            
            # Add category node
            self.scene.add_mindmap_node(category, category, 'category', i, category_pos)
            
            # Connect to central node
            self.scene.add_connection(central_node, category)
            
            # Add leaf nodes
            items = data[category]
            if isinstance(items, list):
                num_leaves = len(items)
                leaf_radius = 200
                angular_span = math.pi / 2.5
                
                for j, item in enumerate(items):
                    if num_leaves == 1:
                        leaf_angle = angle
                    else:
                        leaf_angle = angle + angular_span * (j - (num_leaves - 1) / 2) / (num_leaves - 1)
                    
                    leaf_x = x + leaf_radius * math.cos(leaf_angle)
                    leaf_y = y + leaf_radius * math.sin(leaf_angle)
                    leaf_pos = QPointF(leaf_x, leaf_y)
                    
                    # Add leaf node
                    leaf_id = f"{category}_{item}"
                    self.scene.add_mindmap_node(leaf_id, item, 'leaf', i, leaf_pos)
                    
                    # Connect to category
                    self.scene.add_connection(category, leaf_id)
            else:
                # Handle non-list values
                leaf_pos = QPointF(x + 200 * math.cos(angle), y + 200 * math.sin(angle))
                leaf_id = f"{category}_{items}"
                self.scene.add_mindmap_node(leaf_id, str(items), 'leaf', i, leaf_pos)
                self.scene.add_connection(category, leaf_id)
        
        # Center the view on the mind map
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
    
def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MindMapVisualizer()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()