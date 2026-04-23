"""
Inference using trained PFI model.
"""

import json
import numpy as np
from pathlib import Path
import tensorflow as tf
from keras.preprocessing.sequence import pad_sequences

from claster.core.logger import get_logger

logger = get_logger(__name__)


class PFIPredictor:
    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir).resolve()
        
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Директория модели не найдена: {self.model_dir}")
        
        self.model = None
        self.vocab = {}
        self.seq_len = 50
        self.num_classes = 2
        self.class_names = ['benign', 'attack']
        self._load()

    def _load(self):
        """Загружает модель и метаданные."""
        # Поиск config.json
        config_path = self.model_dir / 'config.json'
        if not config_path.exists():
            alternatives = list(self.model_dir.glob('**/config.json'))
            if alternatives:
                config_path = alternatives[0]
                self.model_dir = config_path.parent
                logger.info(f"Найден config.json в {self.model_dir}")
            else:
                raise FileNotFoundError(f"config.json не найден в {self.model_dir}")
        
        # Загрузка конфигурации
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.seq_len = config.get('seq_len', 50)
            self.num_classes = config.get('num_classes', 2)
        
        # Загрузка словаря
        vocab_path = self.model_dir / 'vocab.json'
        if vocab_path.exists():
            with open(vocab_path, 'r', encoding='utf-8') as f:
                self.vocab = json.load(f)
        else:
            logger.warning("vocab.json не найден")
            self.vocab = {'<PAD>': 0}
        
        # Загрузка меток
        encoder_path = self.model_dir / 'label_encoder.json'
        if encoder_path.exists():
            with open(encoder_path, 'r', encoding='utf-8') as f:
                self.class_names = json.load(f)
        
        # Загрузка модели
        model_path = self.model_dir / 'model.h5'
        if not model_path.exists():
            model_path = self.model_dir / 'checkpoint.h5'
        
        if not model_path.exists():
            raise FileNotFoundError(f"Файл модели не найден в {self.model_dir}")
        
        logger.info(f"Загрузка модели из {model_path}...")
        
        # Импорт пользовательских слоёв
        from claster.pfi.model import PositionalEncoding, TransformerBlock
        
        custom_objects = {
            'PositionalEncoding': PositionalEncoding,
            'TransformerBlock': TransformerBlock
        }
        
        try:
            self.model = tf.keras.models.load_model(
                str(model_path),
                custom_objects=custom_objects,
                compile=False
            )
            logger.info("Модель успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise

    def predict_sequence(self, events):
        """Предсказывает класс для последовательности событий."""
        if self.model is None:
            raise RuntimeError("Модель не загружена")
        
        # Конвертация в ID
        seq_ids = [self.vocab.get(e, 0) for e in events]
        
        # Паддинг
        padded = pad_sequences(
            [seq_ids],
            maxlen=self.seq_len,
            padding='post',
            truncating='post',
            dtype='int32'
        )
        
        # Предсказание
        probs = self.model.predict(padded, verbose=0)[0]
        pred_idx = np.argmax(probs)
        
        label = self.class_names[pred_idx] if pred_idx < len(self.class_names) else 'unknown'
        prob_dict = {
            self.class_names[i] if i < len(self.class_names) else f'class_{i}': float(p)
            for i, p in enumerate(probs)
        }
        
        return float(probs[pred_idx]), label, prob_dict


_predictor = None


def load_model(model_path: str = None):
    """Загружает глобальную модель PFI."""
    global _predictor
    
    if model_path is None:
        from claster.core.config import get_config
        config = get_config()
        model_path = config.get('pfi_model_path')
        
        if not model_path:
            default_paths = [
                Path('./models/pfi_model'),
                Path('./models/pfi_synthetic'),
                Path.home() / '.claster/models/pfi',
            ]
            
            for path in default_paths:
                if path.exists() and (path / 'config.json').exists():
                    model_path = str(path)
                    logger.info(f"Найдена модель в {path}")
                    break
        
        if not model_path:
            raise FileNotFoundError("Модель PFI не найдена.")
    
    model_path = str(Path(model_path).resolve())
    logger.info(f"Загрузка модели из: {model_path}")
    
    _predictor = PFIPredictor(model_path)
    return _predictor


def predict_attack_probability(sequence):
    """Предсказывает вероятность атаки."""
    global _predictor
    if _predictor is None:
        load_model()
    return _predictor.predict_sequence(sequence)


def get_predictor():
    """Возвращает текущий предиктор."""
    global _predictor
    return _predictor