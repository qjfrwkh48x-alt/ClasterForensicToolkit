"""
Dataset loaders with memory optimization.
"""

import numpy as np
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from typing import Tuple, Dict, Generator
import gc

from claster.core.logger import get_logger
from claster.pfi.synthetic import generate_dataset

logger = get_logger(__name__)


def load_synthetic_sequences(
    seq_len: int = 50, 
    num_sequences: int = 10000,
    batch_size: int = 1000,
    vocab_size_limit: int = 5000
):
    """
    Генерирует синтетические последовательности с оптимизацией памяти.
    """
    logger.info(f"Генерация {num_sequences} синтетических последовательностей...")
    
    # Генерируем все данные
    sequences, labels = generate_dataset(num_sequences, seq_len)
    
    # Построение словаря
    logger.info("Построение словаря...")
    vocab = {'<PAD>': 0, '<UNK>': 1}
    token_counts = {}
    
    for seq in sequences:
        for token in seq:
            token_counts[token] = token_counts.get(token, 0) + 1
    
    # Оставляем только самые частые токены
    sorted_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)
    for token, _ in sorted_tokens[:vocab_size_limit - 2]:
        if token not in vocab:
            vocab[token] = len(vocab)
    
    logger.info(f"Размер словаря: {len(vocab)}")
    
    # Конвертация в ID
    logger.info("Конвертация последовательностей в ID...")
    X = []
    for seq in sequences:
        seq_ids = [vocab.get(token, 1) for token in seq]
        X.append(seq_ids)
    
    # Освобождаем память
    del sequences
    gc.collect()
    
    # Паддинг
    logger.info("Паддинг последовательностей...")
    X = pad_sequences(
        X, 
        maxlen=seq_len, 
        padding='post', 
        truncating='post',
        dtype='int32'
    )
    
    # Кодирование меток
    logger.info("Кодирование меток...")
    le = LabelEncoder()
    y = le.fit_transform(labels)
    y = to_categorical(y).astype('float16')
    
    logger.info(f"Размер X: {X.shape}, размер y: {y.shape}")
    logger.info(f"Память X: {X.nbytes / 1024**2:.1f} MB, память y: {y.nbytes / 1024**2:.1f} MB")
    
    return X, y, vocab, le


def load_dataset(
    name: str, 
    data_dir: Path = None, 
    seq_len: int = 50, 
    **kwargs
):
    """Унифицированный загрузчик датасетов."""
    if name == 'synthetic':
        num_sequences = kwargs.get('num_sequences', 5000)
        return load_synthetic_sequences(
            seq_len=seq_len, 
            num_sequences=num_sequences,
            vocab_size_limit=kwargs.get('vocab_size_limit', 3000)
        )
    else:
        raise ValueError(f"Unknown dataset: {name}. Use 'synthetic' for now.")