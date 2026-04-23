"""
Training script with memory optimization.
"""

import json
import argparse
from pathlib import Path
import numpy as np
import tensorflow as tf
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from keras.mixed_precision import set_global_policy
from sklearn.model_selection import train_test_split
import gc

from claster.pfi.model import create_advanced_model
from claster.pfi.dataset import load_dataset
from claster.core.logger import get_logger

logger = get_logger(__name__)

# Включаем mixed precision для экономии памяти
try:
    set_global_policy('mixed_float16')
    logger.info("Mixed precision включена")
except:
    pass


def train_model(
    dataset: str = 'synthetic',
    data_dir: str = None,
    output_dir: str = './models/pfi_model',
    seq_len: int = 40,  # Уменьшено с 50
    epochs: int = 20,    # Уменьшено с 30
    batch_size: int = 32, # Уменьшено с 64
    num_sequences: int = 3000,  # Уменьшено с 10000
    progress_callback=None
):
    """
    Train PFI model with memory optimization.
    """
    # Настройка TensorFlow для экономии памяти
    tf_config = tf.compat.v1.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    tf_config.gpu_options.per_process_gpu_memory_fraction = 0.7
    tf.compat.v1.Session(config=tf_config)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Загрузка датасета {dataset}...")
    X, y, vocab, label_encoder = load_dataset(
        dataset, 
        seq_len=seq_len, 
        num_sequences=num_sequences,
        batch_size=100  # Обработка батчами
    )

    if len(X) == 0:
        raise ValueError("Датасет пуст.")

    logger.info(f"Размер данных: X={X.shape}, y={y.shape}")
    logger.info(f"Размер словаря: {len(vocab)}, классов: {y.shape[1]}")

    # Разделение на train/val
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, 
        test_size=0.2, 
        random_state=42, 
        stratify=y.argmax(axis=1)
    )
    
    # Очистка памяти
    del X, y
    gc.collect()
    
    logger.info(f"Train: {X_train.shape}, Val: {X_val.shape}")

    # Создание модели с уменьшенной размерностью
    model = create_advanced_model(
        vocab_size=len(vocab),
        seq_len=seq_len,
        num_classes=y_train.shape[1],
        embed_dim=64,      # Уменьшено с 128
        num_heads=4,       # Уменьшено с 8
        ff_dim=128,        # Уменьшено с 256
        num_transformer_blocks=2,  # Уменьшено с 4
        dropout=0.2
    )
    
    model.summary(print_fn=logger.info)

    # Коллбэки
    callbacks = [
        EarlyStopping(
            monitor='val_loss', 
            patience=5, 
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss', 
            factor=0.5, 
            patience=3, 
            min_lr=1e-6,
            verbose=1
        ),
        ModelCheckpoint(
            filepath=str(output_dir / 'checkpoint.h5'),
            monitor='val_loss',
            save_best_only=True,
            verbose=1
        )
    ]

    # Очистка кэша TensorFlow перед обучением
    tf.keras.backend.clear_session()
    
    # Обучение
    logger.info("Начало обучения...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1,
        shuffle=True
    )

    # Сохранение модели
    model_path = output_dir / 'model.h5'
    model.save(model_path)
    logger.info(f"Модель сохранена в {model_path}")

    # Сохранение метаданных
    vocab_path = output_dir / 'vocab.json'
    with open(vocab_path, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, ensure_ascii=False)
    logger.info(f"Словарь сохранён в {vocab_path}")

    encoder_path = output_dir / 'label_encoder.json'
    with open(encoder_path, 'w', encoding='utf-8') as f:
        json.dump(list(label_encoder.classes_), f)
    logger.info(f"LabelEncoder сохранён в {encoder_path}")

    config_path = output_dir / 'config.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump({
            'seq_len': seq_len,
            'num_classes': int(y_train.shape[1]),
            'vocab_size': len(vocab),
            'embed_dim': 64,
            'num_heads': 4,
            'ff_dim': 128,
            'num_transformer_blocks': 2
        }, f)
    logger.info(f"Конфигурация сохранена в {config_path}")

    # Очистка памяти
    tf.keras.backend.clear_session()
    gc.collect()
    
    logger.info(f"✅ Обучение завершено! Модель сохранена в {output_dir}")
    return history


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train PFI model')
    parser.add_argument('--dataset', default='synthetic')
    parser.add_argument('--output', default='./models/pfi_model')
    parser.add_argument('--seq-len', type=int, default=40)
    parser.add_argument('--epochs', type=int, default=20)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--num-sequences', type=int, default=3000)
    args = parser.parse_args()

    train_model(
        dataset=args.dataset,
        output_dir=args.output,
        seq_len=args.seq_len,
        epochs=args.epochs,
        batch_size=args.batch_size,
        num_sequences=args.num_sequences
    )