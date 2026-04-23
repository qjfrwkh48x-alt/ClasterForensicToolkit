"""
Real-time monitoring with PFI - динамическое обновление рисков.
"""

import time
import threading
import random
from collections import deque
from datetime import datetime
from pathlib import Path

from claster.core.logger import get_logger
from claster.core.events import event_bus, Event
from claster.pfi.inference import load_model, get_predictor
from claster.pfi.synthetic import generate_live_events, ATTACK_TECHNIQUES

logger = get_logger(__name__)

_buffer = deque(maxlen=500)
_monitor = None
_monitor_thread = None
_running = False

# Текущий статус риска
current_risk = {
    "probability": 0.15,
    "label": "benign",
    "techniques_detected": [],
    "recommendations": [],
    "events_count": 0,
    "last_update": datetime.now().isoformat()
}


class RealtimeMonitor:
    def __init__(self, predictor, interval=3, threshold=0.7):
        self.predictor = predictor
        self.interval = interval
        self.threshold = threshold
        self.running = False
        self.thread = None
        self.seq_len = predictor.seq_len if predictor else 50
        self.event_counter = 0

    def start(self):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info(f"PFI мониторинг запущен (интервал={self.interval}с, порог={self.threshold})")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        logger.info("PFI мониторинг остановлен")

    def _loop(self):
        global current_risk
        
        while self.running:
            try:
                # Генерируем новые события
                new_events = generate_live_events(random.randint(3, 8))
                
                for evt in new_events:
                    event_str = self._event_to_string(evt)
                    _buffer.append(event_str)
                    self.event_counter += 1
                
                # Обновляем статистику
                current_risk["events_count"] = len(_buffer)
                
                # Анализируем буфер
                if len(_buffer) >= 10:
                    seq = list(_buffer)[-self.seq_len:]
                    
                    # Подсчёт индикаторов атак в буфере
                    attack_indicators = self._count_attack_indicators(seq)
                    
                    # Предсказание модели
                    try:
                        prob, label, probs = self.predictor.predict_sequence(seq)
                    except:
                        # Если модель не работает, используем эвристику
                        prob = min(0.3 + attack_indicators * 0.15, 0.99)
                        label = "attack" if prob > 0.5 else "benign"
                        probs = {"benign": 1 - prob, "attack": prob}
                    
                    # Обновляем текущий риск
                    current_risk["probability"] = prob
                    current_risk["label"] = label
                    current_risk["last_update"] = datetime.now().isoformat()
                    
                    # Если обнаружена атака
                    if prob >= self.threshold:
                        techniques = self._detect_techniques(seq)
                        recommendations = self._get_recommendations(techniques)
                        
                        current_risk["techniques_detected"] = techniques
                        current_risk["recommendations"] = recommendations
                        
                        event_bus.publish(Event(
                            name='pfi.alert',
                            data={
                                'probability': prob,
                                'label': label,
                                'techniques': techniques,
                                'recommendations': recommendations,
                                'timestamp': datetime.now().isoformat()
                            }
                        ))
                        
                        logger.warning(f"⚠️ PFI Alert: {label} ({prob:.1%}) - {len(techniques)} техник")
                    else:
                        # Периодически обновляем рекомендации даже при низком риске
                        if self.event_counter % 10 == 0:
                            current_risk["techniques_detected"] = []
                            current_risk["recommendations"] = [
                                "Система работает в нормальном режиме",
                                "Рекомендуется регулярное обновление сигнатур"
                            ]
                
                # Публикуем обновление дашборда
                event_bus.publish(Event(
                    name='pfi.status_update',
                    data=current_risk.copy()
                ))
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
            
            time.sleep(self.interval)

    def _event_to_string(self, event: dict) -> str:
        """Преобразует событие в строку."""
        parts = [event.get('type', 'unknown')]
        if 'image' in event:
            parts.append(f"proc:{event['image']}")
        if 'protocol' in event:
            parts.append(f"proto:{event['protocol']}")
        if 'mitre_technique' in event:
            parts.append(f"mitre:{event['mitre_technique']}")
        if 'severity' in event:
            parts.append(f"sev:{event['severity']}")
        return "|".join(parts)

    def _count_attack_indicators(self, seq: list) -> int:
        """Подсчитывает индикаторы атак в последовательности."""
        indicators = 0
        suspicious_patterns = ['powershell', 'cmd.exe', 'wmic', 'mitre:', 'sev:CRITICAL', 'sev:HIGH']
        
        for event in seq:
            for pattern in suspicious_patterns:
                if pattern in event:
                    indicators += 1
                    break
        
        return min(indicators, 10)

    def _detect_techniques(self, seq: list) -> list:
        """Определяет техники MITRE ATT&CK в последовательности."""
        techniques = set()
        
        for event in seq:
            if 'mitre:' in event:
                parts = event.split('|')
                for part in parts:
                    if part.startswith('mitre:'):
                        tech_id = part.replace('mitre:', '')
                        if tech_id in ATTACK_TECHNIQUES:
                            techniques.add(f"{tech_id}: {ATTACK_TECHNIQUES[tech_id]['name']}")
        
        return list(techniques)[:5]

    def _get_recommendations(self, techniques: list) -> list:
        """Получает рекомендации на основе обнаруженных техник."""
        recommendations = set()
        
        for tech in techniques:
            tech_id = tech.split(':')[0]
            if tech_id in ATTACK_TECHNIQUES:
                recommendations.add(ATTACK_TECHNIQUES[tech_id]['recommendation'])
        
        if not recommendations:
            recommendations.add("Продолжить мониторинг системы")
            recommendations.add("Проверить логи на наличие подозрительной активности")
        
        return list(recommendations)


def start_monitoring(interval=3, threshold=0.7):
    """Запускает мониторинг PFI."""
    global _monitor, _running
    
    try:
        predictor = get_predictor()
        if predictor is None:
            predictor = load_model()
    except Exception as e:
        logger.error(f"Не удалось загрузить модель: {e}")
        return False
    
    if predictor is None:
        logger.error("Модель PFI не загружена")
        return False
    
    _monitor = RealtimeMonitor(predictor, interval, threshold)
    _monitor.start()
    _running = True
    return True


def stop_monitoring():
    """Останавливает мониторинг PFI."""
    global _monitor, _running
    
    if _monitor:
        _monitor.stop()
        _monitor = None
    _running = False
    return True


def is_monitoring():
    """Проверяет, запущен ли мониторинг."""
    return _running and _monitor is not None


def extract_sequence(window_size=50):
    """Извлекает последние события из буфера."""
    return list(_buffer)[-window_size:]


def add_event(event_str: str):
    """Добавляет событие в буфер."""
    _buffer.append(event_str)


def get_current_risk():
    """Возвращает текущий риск."""
    return current_risk.copy()


def get_buffer_size():
    """Возвращает размер буфера."""
    return len(_buffer)