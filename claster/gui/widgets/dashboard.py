"""
Advanced PFI dashboard with real-time risk updates and MITRE ATT&CK.
"""

import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QProgressBar, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QFrame
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime
from collections import deque

from claster.core.system import get_system_info
from claster.core.events import event_bus, Event
from claster.pfi.monitor import (
    extract_sequence, start_monitoring, stop_monitoring, 
    is_monitoring, get_current_risk, get_buffer_size
)
from claster.pfi.inference import load_model, get_predictor


class DashboardWidget(QWidget):

    risk_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # История рисков для графика
        self.risk_history = deque(maxlen=50)
        for i in range(50):
            self.risk_history.append(0.15 + random.uniform(-0.05, 0.05))
        
        self.setup_ui()
        
        # Подписка на события
        event_bus.subscribe("pfi.status_update", self.on_pfi_status_update)
        event_bus.subscribe("pfi.alert", self.on_pfi_alert)
        
        # Таймер обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh)
        self.update_timer.start(2000)
        
        self.refresh()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        
        # ===== ЛЕВАЯ ПАНЕЛЬ =====
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        # Системная информация
        sys_group = QGroupBox("🖥️ Система")
        sys_layout = QGridLayout()
        self.lbl_os = QLabel("ОС: --")
        self.lbl_cpu = QLabel("CPU: --")
        self.lbl_ram = QLabel("RAM: --")
        self.lbl_uptime = QLabel("Аптайм: --")
        sys_layout.addWidget(self.lbl_os, 0, 0)
        sys_layout.addWidget(self.lbl_cpu, 1, 0)
        sys_layout.addWidget(self.lbl_ram, 2, 0)
        sys_layout.addWidget(self.lbl_uptime, 3, 0)
        sys_group.setLayout(sys_layout)
        left_panel.addWidget(sys_group)
        
        # Статус PFI
        pfi_group = QGroupBox("🧠 PFI Мониторинг")
        pfi_layout = QVBoxLayout()
        
        self.lbl_risk = QLabel("Текущий риск: НИЗКИЙ")
        self.lbl_risk.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.lbl_risk.setStyleSheet("color: #00aa00;")
        
        self.risk_bar = QProgressBar()
        self.risk_bar.setMaximum(100)
        self.risk_bar.setValue(15)
        self.risk_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #0f3460;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00aa00, stop:0.5 #ffaa00, stop:1 #ff0000);
                border-radius: 3px;
            }
        """)
        
        self.lbl_events_count = QLabel("Событий в буфере: 0")
        self.lbl_last_update = QLabel("Последнее обновление: --")
        
        pfi_layout.addWidget(self.lbl_risk)
        pfi_layout.addWidget(self.risk_bar)
        pfi_layout.addWidget(self.lbl_events_count)
        pfi_layout.addWidget(self.lbl_last_update)
        
        self.btn_monitor = QPushButton("▶ Запустить мониторинг")
        self.btn_monitor.clicked.connect(self.toggle_monitoring)
        self.btn_monitor.setStyleSheet("""
            QPushButton {
                background-color: #0d7377;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
        """)
        pfi_layout.addWidget(self.btn_monitor)
        
        pfi_group.setLayout(pfi_layout)
        left_panel.addWidget(pfi_group)
        
        # Рекомендации
        rec_group = QGroupBox("📋 Рекомендации")
        rec_layout = QVBoxLayout()
        self.rec_text = QTextEdit()
        self.rec_text.setReadOnly(True)
        self.rec_text.setMaximumHeight(180)
        self.rec_text.setPlaceholderText("Рекомендации по безопасности...")
        rec_layout.addWidget(self.rec_text)
        rec_group.setLayout(rec_layout)
        left_panel.addWidget(rec_group)
        
        left_panel.addStretch()
        
        # ===== ПРАВАЯ ПАНЕЛЬ =====
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)
        
        # График риска
        graph_group = QGroupBox("📈 Динамика риска")
        graph_layout = QVBoxLayout()
        
        self.figure = Figure(figsize=(8, 3), facecolor='#1a1a2e')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#0f0f1a')
        self.ax.tick_params(colors='#e0e0e0')
        self.ax.spines['bottom'].set_color('#e0e0e0')
        self.ax.spines['left'].set_color('#e0e0e0')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.set_ylim(0, 1)
        self.ax.set_ylabel('Вероятность атаки', color='#e0e0e0')
        self.ax.set_xlabel('Время (события)', color='#e0e0e0')
        self.ax.axhline(y=0.7, color='#ffaa00', linestyle='--', alpha=0.7, label='Порог')
        self.ax.axhline(y=0.85, color='#ff0000', linestyle='--', alpha=0.7, label='Критический')
        self.ax.legend(loc='upper left', facecolor='#1a1a2e', labelcolor='#e0e0e0')
        
        self.risk_line, = self.ax.plot([], [], color='#e94560', linewidth=2)
        self.ax.fill_between([], [], color='#e94560', alpha=0.3)
        
        graph_layout.addWidget(self.canvas)
        graph_group.setLayout(graph_layout)
        right_panel.addWidget(graph_group)
        
        # Таблица MITRE ATT&CK
        table_group = QGroupBox("🎯 Обнаруженные техники (MITRE ATT&CK)")
        table_layout = QVBoxLayout()
        
        self.attack_table = QTableWidget()
        self.attack_table.setColumnCount(4)
        self.attack_table.setHorizontalHeaderLabels(["Техника", "Тактика", "Серьёзность", "Рекомендация"])
        self.attack_table.horizontalHeader().setStretchLastSection(True)
        self.attack_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.attack_table.setAlternatingRowColors(True)
        self.attack_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table_layout.addWidget(self.attack_table)
        
        table_group.setLayout(table_layout)
        right_panel.addWidget(table_group)
        
        # Последние события
        events_group = QGroupBox("📌 Последние события")
        events_layout = QVBoxLayout()
        self.events_text = QTextEdit()
        self.events_text.setReadOnly(True)
        self.events_text.setMaximumHeight(150)
        self.events_text.setFont(QFont("Consolas", 9))
        events_layout.addWidget(self.events_text)
        events_group.setLayout(events_layout)
        right_panel.addWidget(events_group)
        
        # Компоновка
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(350)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget, 1)
        self.setLayout(main_layout)

    def toggle_monitoring(self):
        """Переключает мониторинг."""
        if is_monitoring():
            stop_monitoring()
            self.btn_monitor.setText("▶ Запустить мониторинг")
            self.btn_monitor.setStyleSheet("""
                QPushButton {
                    background-color: #0d7377;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #14a085;
                }
            """)
        else:
            # Проверяем модель
            try:
                if get_predictor() is None:
                    load_model()
            except:
                pass
            
            if start_monitoring(interval=2, threshold=0.7):
                self.btn_monitor.setText("⏹ Остановить мониторинг")
                self.btn_monitor.setStyleSheet("""
                    QPushButton {
                        background-color: #e94560;
                        color: white;
                        font-weight: bold;
                        padding: 8px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #ff6b6b;
                    }
                """)
                
                # Очищаем буфер и начинаем с чистого листа
                self.risk_history.clear()
                for _ in range(50):
                    self.risk_history.append(0.15)

    def on_pfi_status_update(self, event: Event):
        """Обработчик обновления статуса PFI."""
        data = event.data
        self.risk_updated.emit(data)

    def on_pfi_alert(self, event: Event):
        """Обработчик алерта PFI."""
        data = event.data
        
        # Обновляем таблицу техник
        techniques = data.get('techniques', [])
        recommendations = data.get('recommendations', [])
        
        if techniques:
            self.update_attack_table(techniques, recommendations)

    def update_attack_table(self, techniques: list, recommendations: list):
        """Обновляет таблицу техник MITRE ATT&CK."""
        from claster.pfi.synthetic import ATTACK_TECHNIQUES
        
        self.attack_table.setRowCount(0)
        
        for i, tech in enumerate(techniques):
            tech_id = tech.split(':')[0] if ':' in tech else tech
            tech_info = ATTACK_TECHNIQUES.get(tech_id, {})
            
            row = self.attack_table.rowCount()
            self.attack_table.insertRow(row)
            
            # Техника
            self.attack_table.setItem(row, 0, QTableWidgetItem(tech))
            
            # Тактика
            self.attack_table.setItem(row, 1, QTableWidgetItem(tech_info.get('tactic', 'Unknown')))
            
            # Серьёзность
            severity = tech_info.get('severity', 'MEDIUM')
            severity_item = QTableWidgetItem(severity)
            if severity == 'CRITICAL':
                severity_item.setBackground(QColor('#ff0000'))
                severity_item.setForeground(QColor('#ffffff'))
            elif severity == 'HIGH':
                severity_item.setBackground(QColor('#ff6600'))
                severity_item.setForeground(QColor('#ffffff'))
            elif severity == 'MEDIUM':
                severity_item.setBackground(QColor('#ffcc00'))
            self.attack_table.setItem(row, 2, severity_item)
            
            # Рекомендация
            rec = recommendations[i] if i < len(recommendations) else tech_info.get('recommendation', '')
            self.attack_table.setItem(row, 3, QTableWidgetItem(rec))

    def refresh(self):
        try:
            sys_info = get_system_info()
            self.lbl_os.setText(f"ОС: {sys_info.get('os', '--')}")
            self.lbl_cpu.setText(f"CPU: {sys_info.get('cpu_physical_cores', '--')} ядер")
            self.lbl_ram.setText(f"RAM: {sys_info.get('total_ram_gb', '--')} GB")
        except:
            pass
        
        # Риск PFI
        risk = get_current_risk()
        prob = risk.get('probability', 0.15)
        label = risk.get('label', 'benign')
        
        self.risk_history.append(prob)
        
        # Обновление индикатора
        if prob < 0.3:
            color = "#00aa00"
            text = "НИЗКИЙ"
        elif prob < 0.6:
            color = "#ffaa00"
            text = "СРЕДНИЙ"
        elif prob < 0.8:
            color = "#ff6600"
            text = "ВЫСОКИЙ"
        else:
            color = "#ff0000"
            text = "КРИТИЧЕСКИЙ"
        
        self.lbl_risk.setText(f"Текущий риск: {text} ({prob:.1%})")
        self.lbl_risk.setStyleSheet(f"color: {color};")
        self.risk_bar.setValue(int(prob * 100))
        
        # События
        events_count = get_buffer_size()
        self.lbl_events_count.setText(f"Событий в буфере: {events_count}")
        self.lbl_last_update.setText(f"Обновление: {datetime.now().strftime('%H:%M:%S')}")
        
        # Рекомендации
        recommendations = risk.get('recommendations', [
            "Система работает в нормальном режиме",
            "Рекомендуется регулярное обновление сигнатур"
        ])
        self.rec_text.setText("• " + "\n• ".join(recommendations))
        
        # Последние события
        events = extract_sequence(8)
        if events:
            self.events_text.setText("\n".join(events[-8:]))
        
        # Обновление графика
        if len(self.risk_history) > 0:
            x = range(len(self.risk_history))
            y = list(self.risk_history)
            
            self.risk_line.set_data(x, y)
            
            # Удаляем старые коллекции (fill_between)
            for collection in self.ax.collections[:]:
                collection.remove()
            
            # Добавляем новую заливку
            self.ax.fill_between(x, y, color='#e94560', alpha=0.3)
            
            self.ax.set_xlim(0, max(49, len(self.risk_history) - 1))
            self.canvas.draw_idle()
        
        # Обновление кнопки
        if is_monitoring():
            self.btn_monitor.setText("⏹ Остановить мониторинг")
            self.btn_monitor.setStyleSheet("""
                QPushButton {
                    background-color: #e94560;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #ff6b6b;
                }
            """)
        else:
            self.btn_monitor.setText("▶ Запустить мониторинг")
            self.btn_monitor.setStyleSheet("""
                QPushButton {
                    background-color: #0d7377;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #14a085;
                }
            """)