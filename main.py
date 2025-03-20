import sys
import json
import bisect
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl
import fitz  # PyMuPDF for PDF rendering

class ScoreViewer(QWidget):
    def __init__(self, pdf_path, json_path, audio_path, timestamps_path):
        super().__init__()
        self.pdf_path = pdf_path
        self.json_path = json_path
        self.audio_path = audio_path
        self.timestamps_path = timestamps_path
        
        self.current_page = 0
        self.load_measure_data()
        self.init_ui()
        self.load_page()
        self.load_audio()
        
    def load_measure_data(self):
        with open(self.json_path, 'r') as f:
            self.measure_boxes = json.load(f)["pages"]

        self.measure_timestamps = {}
        self.sorted_timestamps = []  # Store timestamps in order for binary search
        with open(self.timestamps_path, 'r') as f:
            for line in f:
                measure, timestamp = line.strip().split()
                measure = int(measure)
                timestamp = float(timestamp)
                self.measure_timestamps[measure] = timestamp
                self.sorted_timestamps.append((timestamp, measure))  # Store as tuple

    def init_ui(self):
        layout = QVBoxLayout()
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        
        self.prev_button = QPushButton("Previous Page")
        self.next_button = QPushButton("Next Page")
        
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        
        layout.addWidget(self.view)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.next_button)
        self.setLayout(layout)
    
    def load_page(self):
        self.scene.clear()
    
        # Load the expected page size from JSON
        page_size = self.measure_boxes[self.current_page]["size"]
        expected_width = page_size["width"]
        expected_height = page_size["height"]
        
        # Load and render the PDF page
        doc = fitz.open(self.pdf_path)
        pix = doc[self.current_page].get_pixmap()
        
        # Convert to QImage
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)

        img = QPixmap.fromImage(image)
        
        # Scale image to match the expected dimensions
        img = img.scaled(expected_width, expected_height, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Display the scaled image
        self.scene.addPixmap(img)
        
        # Add measure boxes
        self.add_measure_boxes()
    
    def add_measure_boxes(self):
        page_data = self.measure_boxes[self.current_page]
        
        # Compute the global measure index by summing previous pages' measures
        global_measure_index = sum(len(page["measures"]) for page in self.measure_boxes[:self.current_page])
        
        self.measure_items = []  # Store measure items for updating colors

        for i, measure in enumerate(page_data["measures"], start=1):
            measure_number = global_measure_index + i  # Ensure numbering is continuous
            
            x, y, w, h = measure["left"], measure["top"], measure["right"] - measure["left"], measure["bottom"] - measure["top"]
            rect = QGraphicsRectItem(x, y, w, h)
            rect.setBrush(Qt.GlobalColor.transparent)
            rect.setPen(Qt.GlobalColor.green)
            
            rect.setData(0, measure_number)  # Store the correct global measure number
            rect.mousePressEvent = self.measure_clicked
            self.scene.addItem(rect)

            self.measure_items.append((measure_number, rect))  # Store for later updates

    def measure_clicked(self, event):
        item = self.scene.itemAt(event.scenePos(), self.view.transform())
        if item and isinstance(item, QGraphicsRectItem):
            measure = item.data(0)
            if measure in self.measure_timestamps:
                timestamp = self.measure_timestamps[measure]
                self.player.setPosition(int(timestamp * 1000))  # Convert to ms
                self.player.play()

    def update_highlighted_measure(self, position: int):
        """ Uses binary search to efficiently find and update the currently playing measure """
        current_time = position / 1000.0  # Convert from ms to sec

        # Use binary search to find the latest measure that has started
        index = bisect.bisect_right(self.sorted_timestamps, (current_time, float('inf'))) - 1
        current_measure = self.sorted_timestamps[index][1] if index >= 0 else None

        # Update only if the measure has changed
        if current_measure != getattr(self, "current_highlighted_measure", None):
            self.current_highlighted_measure = current_measure

            # Find which page this measure is on
            new_page = None
            global_measure_index = 0

            for page_num, page_data in enumerate(self.measure_boxes):
                num_measures = len(page_data["measures"])
                if global_measure_index < current_measure <= global_measure_index + num_measures:
                    new_page = page_num
                    break
                global_measure_index += num_measures

            # If the page is different, update it
            if new_page is not None and new_page != self.current_page:
                self.current_page = new_page
                self.load_page()

            for measure_number, rect in self.measure_items:
                rect.setPen(Qt.GlobalColor.red if measure_number == current_measure else Qt.GlobalColor.green)

    def load_audio(self):
        """ Load the audio and connect position updates """
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()  # Required in PyQt6
        self.player.setAudioOutput(self.audio_output)

        self.player.setSource(QUrl.fromLocalFile(self.audio_path))
        
        # Connect the update function to trigger while playing
        self.player.positionChanged.connect(self.update_highlighted_measure)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()
    
    def next_page(self):
        if self.current_page < len(self.measure_boxes) - 1:
            self.current_page += 1
            self.load_page()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScoreViewer("test/score.pdf", "test/measure_boxes.json", "test/audio.mp3", "test/timestamps.txt")
    window.show()
    sys.exit(app.exec())
