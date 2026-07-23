import tensorflow as tf
import numpy as np

# 特徵向量：[電池%, RAM%, CPU負載%, 溫度°C, 訊號dBm]
model = tf.keras.Sequential([
    tf.keras.layers.Dense(32, activation='relu', input_shape=(5,)),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.Dense(16, activation='relu'),
    tf.keras.layers.Dense(3, activation='softmax') # 輸出：0:正常, 1:省電, 2:終極壓制(冷氣)
])

model.compile(optimizer='adam', loss='categorical_crossentropy')

# 轉換為支援 NPU 加速的 TFLite 格式
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

with open('mode_predictor.tflite', 'wb') as f:
    f.write(tflite_model)

