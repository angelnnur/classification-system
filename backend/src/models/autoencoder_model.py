from keras.models import Model, load_model
from keras.layers import Dense, Input, Dropout
from keras.losses import CategoricalCrossentropy
from keras.optimizers import Adam
from keras.regularizers import l2
import matplotlib.pyplot as plt


class AutoencoderDL:
    def __init__(self, input_dim, bottleneck_dim, num_classes):
        self.input_dim = input_dim
        self.bottleneck_dim = bottleneck_dim
        self.num_classes = num_classes
        self.classifier = None

    def build_model(self, dropout_rate=0.5, l2_reg=0.0001):
        input_layer = Input(shape=(self.input_dim,), name='input')


        encoder_layer = Dense(self.bottleneck_dim*8, activation="relu", 
                             kernel_regularizer=l2(l2_reg))(input_layer)
        encoder_layer = Dropout(dropout_rate)(encoder_layer)
        
        encoder_layer = Dense(self.bottleneck_dim*4, activation="relu",
                             kernel_regularizer=l2(l2_reg))(encoder_layer)
        encoder_layer = Dropout(dropout_rate)(encoder_layer)
        
        encoder_layer = Dense(self.bottleneck_dim*2, activation="relu",
                             kernel_regularizer=l2(l2_reg))(encoder_layer)
        encoder_layer = Dropout(dropout_rate * 0.8)(encoder_layer)
        
        bottleneck_layer = Dense(self.bottleneck_dim, name="bottleneck_layer",
                                 kernel_regularizer=l2(l2_reg))(encoder_layer)

        # Классификация
        output = Dense(self.num_classes, activation='softmax', name='output',
                      kernel_regularizer=l2(l2_reg))(bottleneck_layer)

        self.classifier = Model(inputs=input_layer, outputs=output, name='classifier')

        optimizer = Adam(learning_rate=0.0005)
        self.classifier.compile(
            loss=CategoricalCrossentropy(),
            optimizer=optimizer,
            metrics=['accuracy']
        )

        return self.classifier

    def train_classifier(self, X, y, epochs=50, batch_size=64, validation_split=0.2, use_early_stopping=True):
        if self.classifier is None:
            self.build_model()
       
        callbacks = []
        
        if use_early_stopping and validation_split > 0:
            from keras.callbacks import EarlyStopping, ReduceLROnPlateau
            
            early_stopping = EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True,
                verbose=1,
                min_delta=0.001
            )
            callbacks.append(early_stopping)
            
            reduce_lr = ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=3,
                min_lr=0.00001,
                verbose=1
            )
            callbacks.append(reduce_lr)
       
        history = self.classifier.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=1,
            shuffle=True,
            callbacks=callbacks
        )

        final_train_acc = history.history['accuracy'][-1]
        final_train_loss = history.history['loss'][-1]

        print(f"\nРЕЗУЛЬТАТЫ")
        print(f"  Train Accuracy: {final_train_acc:.4f} ({final_train_acc * 100:.1f}%)")
        print(f"  Train Loss:     {final_train_loss:.4f}")
        
        if validation_split > 0 and 'val_accuracy' in history.history:
            final_val_acc = history.history['val_accuracy'][-1]
            final_val_loss = history.history['val_loss'][-1]
            print(f"  Val Accuracy:   {final_val_acc:.4f} ({final_val_acc * 100:.1f}%)")
            print(f"  Val Loss:       {final_val_loss:.4f}")
        
        self.plot_training_history(history)

        return history

    def predict_class(self, X):
        probs = self.classifier.predict(X, verbose=0)
        labels = probs.argmax(axis=1)
        return labels, probs

    def save(self, classifier_path):
        self.classifier.save(classifier_path)

    def load_classifier(self, path):
        self.classifier = load_model(path)