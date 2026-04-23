"""
PFI training widget using synthetic data only.
"""

import json
import threading
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QProgressBar, QTextEdit, QFileDialog,
    QGroupBox, QFormLayout, QLineEdit
)
from PyQt6.QtCore import QThread, pyqtSignal

from claster.pfi.train import train_model
from claster.core.logger import get_logger

logger = get_logger(__name__)


class TrainerThread(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    epoch_update = pyqtSignal(dict)
    finished = pyqtSignal(bool, str)

    def __init__(self, output_dir, seq_len, epochs, batch_size, num_sequences):
        super().__init__()
        self.output_dir = output_dir
        self.seq_len = seq_len
        self.epochs = epochs
        self.batch_size = batch_size
        self.num_sequences = num_sequences

    def run(self):
        def progress_callback(epoch, logs):
            self.progress.emit(int((epoch + 1) / self.epochs * 100))
            self.epoch_update.emit(logs)

        try:
            train_model(
                dataset='synthetic',
                output_dir=self.output_dir,
                seq_len=self.seq_len,
                epochs=self.epochs,
                batch_size=self.batch_size,
                num_sequences=self.num_sequences,
                progress_callback=progress_callback
            )
            self.finished.emit(True, f"Модель сохранена в {self.output_dir}")
        except Exception as e:
            self.finished.emit(False, str(e))


class PFITrainerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.history = {'loss': [], 'val_loss': [], 'accuracy': [], 'val_accuracy': []}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        params_group = QGroupBox("Параметры обучения")
        form = QFormLayout()

        # Только синтетические данные
        self.dataset_label = QLabel("Синтетические данные")
        form.addRow("Датасет:", self.dataset_label)

        self.output_edit = QLineEdit("./models/pfi_model")
        browse_out = QPushButton("Обзор")
        browse_out.clicked.connect(lambda: self.browse_directory(self.output_edit))
        ol = QHBoxLayout()
        ol.addWidget(self.output_edit)
        ol.addWidget(browse_out)
        form.addRow("Директория модели:", ol)

        self.seq_len_spin = QSpinBox()
        self.seq_len_spin.setRange(20, 100)
        self.seq_len_spin.setValue(40)  

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(5, 50)
        self.epochs_spin.setValue(20)  

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(8, 128)
        self.batch_spin.setValue(32) 

        self.num_seq_spin = QSpinBox()
        self.num_seq_spin.setRange(1000, 20000)
        self.num_seq_spin.setValue(3000)  

        params_group.setLayout(form)
        layout.addWidget(params_group)

        # Графики
        self.figure = plt.figure(figsize=(10, 4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        btn_layout = QHBoxLayout()
        self.train_btn = QPushButton("Начать обучение")
        self.train_btn.clicked.connect(self.start_training)
        btn_layout.addWidget(self.train_btn)
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def browse_directory(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "Выберите директорию")
        if path:
            line_edit.setText(path)

    def start_training(self):
        self.train_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.history = {'loss': [], 'val_loss': [], 'accuracy': [], 'val_accuracy': []}
        self.update_plots()

        self.thread = TrainerThread(
            output_dir=self.output_edit.text(),
            seq_len=self.seq_len_spin.value(),
            epochs=self.epochs_spin.value(),
            batch_size=self.batch_spin.value(),
            num_sequences=self.num_seq_spin.value()
        )
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.log.connect(self.log_text.append)
        self.thread.epoch_update.connect(self.update_history)
        self.thread.finished.connect(self.training_finished)
        self.stop_btn.clicked.connect(self.thread.terminate)
        self.thread.start()

    def update_history(self, logs):
        for k in ['loss', 'val_loss', 'accuracy', 'val_accuracy']:
            if k in logs:
                self.history[k].append(logs[k])
        self.update_plots()

    def update_plots(self):
        self.figure.clear()
        ax1 = self.figure.add_subplot(121)
        ax1.plot(self.history['loss'], label='Потери')
        ax1.plot(self.history['val_loss'], label='Валидация')
        ax1.set_title('Потери')
        ax1.legend()
        ax2 = self.figure.add_subplot(122)
        ax2.plot(self.history['accuracy'], label='Точность')
        ax2.plot(self.history['val_accuracy'], label='Валидация')
        ax2.set_title('Точность')
        ax2.legend()
        self.canvas.draw()

    def training_finished(self, success, message):
        self.train_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_text.append(message if success else f"Ошибка: {message}")