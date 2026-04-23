"""
Advanced PFI model: Transformer + CNN hybrid.
Compatible with TensorFlow 2.x.
"""

import numpy as np
import tensorflow as tf
from keras import layers, Model, Input


@tf.keras.utils.register_keras_serializable(package='ClasterPFI')
class PositionalEncoding(layers.Layer):
    """Positional encoding layer for Transformer."""
    
    def __init__(self, max_len: int, embed_dim: int, **kwargs):
        super().__init__(**kwargs)
        self.max_len = max_len
        self.embed_dim = embed_dim
        
    def build(self, input_shape):
        # Создаём позиционные эмбеддинги при сборке
        angle_rads = self._get_angles(
            np.arange(self.max_len)[:, np.newaxis],
            np.arange(self.embed_dim)[np.newaxis, :],
            self.embed_dim
        )
        angle_rads[:, 0::2] = np.sin(angle_rads[:, 0::2])
        angle_rads[:, 1::2] = np.cos(angle_rads[:, 1::2])
        self.pos_encoding = self.add_weight(
            name='pos_encoding',
            shape=(1, self.max_len, self.embed_dim),
            initializer=tf.constant_initializer(angle_rads[np.newaxis, ...]),
            trainable=False,
            dtype=tf.float32
        )
        super().build(input_shape)

    def _get_angles(self, pos, i, embed_dim):
        angle_rates = 1 / np.power(10000, (2 * (i // 2)) / embed_dim)
        return pos * angle_rates

    def call(self, x):
        seq_len = tf.shape(x)[1]
        return x + self.pos_encoding[:, :seq_len, :]

    def get_config(self):
        config = super().get_config()
        config.update({
            'max_len': self.max_len,
            'embed_dim': self.embed_dim
        })
        return config


@tf.keras.utils.register_keras_serializable(package='ClasterPFI')
class TransformerBlock(layers.Layer):
    """Transformer encoder block."""
    
    def __init__(self, embed_dim, num_heads, ff_dim, dropout=0.1, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.ff_dim = ff_dim
        self.dropout = dropout
        
    def build(self, input_shape):
        self.att = layers.MultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=self.embed_dim // self.num_heads,
            dropout=self.dropout
        )
        self.dropout1 = layers.Dropout(self.dropout)
        self.layernorm1 = layers.LayerNormalization(epsilon=1e-6)
        
        self.conv1 = layers.Conv1D(filters=self.ff_dim, kernel_size=1, activation='relu')
        self.dropout2 = layers.Dropout(self.dropout)
        self.conv2 = layers.Conv1D(filters=self.embed_dim, kernel_size=1)
        self.dropout3 = layers.Dropout(self.dropout)
        self.layernorm2 = layers.LayerNormalization(epsilon=1e-6)
        super().build(input_shape)
        
    def call(self, inputs, training=None):
        # Multi-Head Attention
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        
        # Feed-Forward Network
        ff_output = self.conv1(out1)
        ff_output = self.dropout2(ff_output, training=training)
        ff_output = self.conv2(ff_output)
        ff_output = self.dropout3(ff_output, training=training)
        return self.layernorm2(out1 + ff_output)
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'embed_dim': self.embed_dim,
            'num_heads': self.num_heads,
            'ff_dim': self.ff_dim,
            'dropout': self.dropout
        })
        return config


def create_advanced_model(
    vocab_size: int,
    seq_len: int,
    num_classes: int,
    embed_dim: int = 64,
    num_heads: int = 4,
    ff_dim: int = 128,
    num_transformer_blocks: int = 2,
    dropout: float = 0.2
) -> Model:
    """
    Создаёт гибридную модель Transformer + CNN.
    """
    # Входной слой
    inputs = Input(shape=(seq_len,), dtype='int32', name='input')
    
    # Эмбеддинг (без маски)
    x = layers.Embedding(
        input_dim=vocab_size, 
        output_dim=embed_dim,
        name='embedding'
    )(inputs)
    
    # Позиционное кодирование
    x = PositionalEncoding(seq_len, embed_dim, name='pos_encoding')(x)
    
    # Transformer блоки
    for i in range(num_transformer_blocks):
        x = TransformerBlock(
            embed_dim=embed_dim,
            num_heads=num_heads,
            ff_dim=ff_dim,
            dropout=dropout,
            name=f'transformer_block_{i}'
        )(x)
    
    # CNN для локальных признаков
    cnn = layers.Conv1D(filters=64, kernel_size=3, activation='relu', padding='same', name='conv1d')(x)
    cnn = layers.GlobalMaxPooling1D(name='global_max_pool')(cnn)
    
    # Глобальный контекст из Transformer
    transformer_out = layers.GlobalAveragePooling1D(name='global_avg_pool')(x)
    
    # Объединение признаков
    combined = layers.Concatenate(name='concatenate')([transformer_out, cnn])
    
    # Классификатор
    combined = layers.Dense(128, activation='relu', name='dense1')(combined)
    combined = layers.Dropout(dropout, name='dropout')(combined)
    outputs = layers.Dense(num_classes, activation='softmax', dtype='float32', name='output')(combined)
    
    model = Model(inputs=inputs, outputs=outputs, name='PFI_Model')
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss=tf.keras.losses.CategoricalCrossentropy(),
        metrics=['accuracy']
    )
    
    return model


# Для обратной совместимости
def create_model(*args, **kwargs):
    """Alias for create_advanced_model."""
    return create_advanced_model(*args, **kwargs)


# Экспорт слоёв
__all__ = [
    'PositionalEncoding',
    'TransformerBlock',
    'create_advanced_model',
    'create_model'
]