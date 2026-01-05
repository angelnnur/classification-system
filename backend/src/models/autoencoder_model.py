import os
# КРИТИЧЕСКИ ВАЖНО: Отключаем GPU ПЕРЕД импортом Keras/TensorFlow
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'false'

# Импортируем TensorFlow и настраиваем его ПЕРЕД импортом Keras
try:
    import tensorflow as tf
    # Явно отключаем все GPU устройства
    tf.config.set_visible_devices([], 'GPU')
    # Ограничиваем использование памяти
    tf.config.set_soft_device_placement(True)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.config.threading.set_intra_op_parallelism_threads(1)
except Exception as e:
    print(f"⚠️  Предупреждение при настройке TensorFlow: {e}")

from keras.models import Model, load_model
from keras.layers import Dense, Input, Dropout, BatchNormalization
from keras.losses import CategoricalCrossentropy
from keras.optimizers import Adam


class AutoencoderDL:
    def __init__(self, input_dim, bottleneck_dim, num_classes):
        self.input_dim = input_dim
        self.bottleneck_dim = bottleneck_dim
        self.num_classes = num_classes
        self.classifier = None

    def build_model(self):

        # Входной слой
        input_layer = Input(shape=(self.input_dim,), name='input')

        # Енкодер
        encoder_layer = Dense(512, activation="relu")(input_layer)
        encoder_layer = Dense(256, activation="relu")(encoder_layer)
        encoder_layer = Dense(128, activation="relu")(encoder_layer)
        bottleneck_layer = Dense(self.bottleneck_dim, name="bottleneck_layer")(encoder_layer)

        # Классификация
        output = Dense(self.num_classes, activation='softmax', name='output')(bottleneck_layer)

        self.classifier = Model(inputs=input_layer, outputs=output, name='classifier')

        optimizer = Adam(learning_rate=0.001)
        self.classifier.compile(
            loss=CategoricalCrossentropy(),
            optimizer=optimizer,
            metrics=['accuracy']
        )

        return self.classifier

    def train_classifier(self, X, y, epochs=50, batch_size=64):

        if self.classifier is None:
            self.build_model()

        print(f"\n[INFO] ПАРАМЕТРЫ ОБУЧЕНИЯ:")
        print(f"  X.shape={X.shape}, y.shape={y.shape}")
        print(f"  epochs={epochs}, batch_size={batch_size}")

        history = self.classifier.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
            shuffle=True
        )

        print("\n[OK] Обучение завершено!")

        # Показать финальные метрики
        final_train_acc = history.history['accuracy'][-1]
        final_train_loss = history.history['loss'][-1]

        print(f"\n[РЕЗУЛЬТАТЫ]")
        print(f"  Train Accuracy: {final_train_acc:.4f} ({final_train_acc * 100:.1f}%)")
        print(f"  Train Loss:     {final_train_loss:.4f}")

        return history

    def predict_class(self, X):
        if self.classifier is None:
            raise ValueError("Classifier not built. Call build_model() first.")

        probs = self.classifier.predict(X, verbose=0)
        labels = probs.argmax(axis=1)
        return labels, probs

    def save(self, classifier_path):
        self.classifier.save(classifier_path)

    def load_classifier(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found at {path}")
        
        # Убеждаемся что GPU отключен перед загрузкой модели
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        try:
            import tensorflow as tf
            tf.config.set_visible_devices([], 'GPU')
        except:
            pass
        
        try:
            self.classifier = load_model(path)
            print(f"✅ Модель загружена из {path}")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            raise
