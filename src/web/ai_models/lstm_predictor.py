"""
LSTM Predictor
Deep learning LSTM model for time-series prediction
"""
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("TensorFlow not available. Install with: pip install tensorflow")


class LSTMPredictor:
    """LSTM neural network for stock prediction"""
    
    def __init__(
        self,
        sequence_length: int = 60,
        lstm_units: int = 50,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        epochs: int = 50
    ):
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is not installed. Install with: pip install tensorflow")
        
        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.model = None
        self.feature_cols: List[str] = []
        self.scaler = None
        self.is_trained = False
    
    def _create_sequences(
        self,
        data: np.ndarray,
        labels: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM input"""
        X, y = [], []
        
        for i in range(self.sequence_length, len(data)):
            X.append(data[i - self.sequence_length:i])
            y.append(labels[i])
        
        return np.array(X), np.array(y)
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        feature_cols: List[str],
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None
    ) -> Dict:
        """
        Train LSTM model
        
        Args:
            X_train: Training features
            y_train: Training labels
            feature_cols: List of feature column names
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
        
        Returns:
            Training metrics dictionary
        """
        self.feature_cols = feature_cols
        
        # Prepare data
        from sklearn.preprocessing import StandardScaler
        
        train_data = X_train[feature_cols].fillna(0).values
        train_labels = y_train.values
        
        # Scale features
        self.scaler = StandardScaler()
        train_data_scaled = self.scaler.fit_transform(train_data)
        
        # Create sequences
        X_seq, y_seq = self._create_sequences(train_data_scaled, train_labels)
        
        if len(X_seq) == 0:
            raise ValueError(f"Not enough data for sequence length {self.sequence_length}")
        
        # Build LSTM model
        self.model = keras.Sequential([
            layers.LSTM(
                self.lstm_units,
                return_sequences=True,
                input_shape=(self.sequence_length, len(feature_cols))
            ),
            layers.Dropout(self.dropout_rate),
            layers.LSTM(self.lstm_units, return_sequences=False),
            layers.Dropout(self.dropout_rate),
            layers.Dense(25, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Prepare validation data
        validation_data = None
        if X_val is not None and y_val is not None:
            val_data = X_val[feature_cols].fillna(0).values
            val_data_scaled = self.scaler.transform(val_data)
            val_labels = y_val.values
            X_val_seq, y_val_seq = self._create_sequences(val_data_scaled, val_labels)
            
            if len(X_val_seq) > 0:
                validation_data = (X_val_seq, y_val_seq)
        
        # Train model
        history = self.model.fit(
            X_seq,
            y_seq,
            batch_size=self.batch_size,
            epochs=self.epochs,
            validation_data=validation_data,
            verbose=0,
            shuffle=False  # Important for time series
        )
        
        self.is_trained = True
        
        # Calculate metrics
        train_pred = self.model.predict(X_seq, verbose=0)
        train_pred_binary = (train_pred > 0.5).astype(int).flatten()
        train_accuracy = np.mean(train_pred_binary == y_seq)
        
        val_accuracy = None
        if validation_data:
            val_pred = self.model.predict(X_val_seq, verbose=0)
            val_pred_binary = (val_pred > 0.5).astype(int).flatten()
            val_accuracy = np.mean(val_pred_binary == y_val_seq)
        
        metrics = {
            'train_accuracy': float(train_accuracy),
            'val_accuracy': float(val_accuracy) if val_accuracy else None,
            'final_loss': float(history.history['loss'][-1]),
            'final_val_loss': float(history.history.get('val_loss', [0])[-1]) if validation_data else None
        }
        
        logger.info(f"LSTM trained: train_acc={train_accuracy:.3f}, val_acc={val_accuracy:.3f if val_accuracy else 'N/A'}")
        
        return metrics
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict probabilities
        
        Args:
            X: Feature dataframe
        
        Returns:
            Array of probabilities for class 1
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Prepare data
        data = X[self.feature_cols].fillna(0).values
        data_scaled = self.scaler.transform(data)
        
        # Create sequences (use last sequence_length rows)
        if len(data_scaled) < self.sequence_length:
            # Pad with zeros if not enough data
            padding = np.zeros((self.sequence_length - len(data_scaled), len(self.feature_cols)))
            data_scaled = np.vstack([padding, data_scaled])
        
        # Use last sequence_length rows
        sequence = data_scaled[-self.sequence_length:].reshape(1, self.sequence_length, len(self.feature_cols))
        
        proba = self.model.predict(sequence, verbose=0)
        return proba.flatten()
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict classes
        
        Args:
            X: Feature dataframe
        
        Returns:
            Array of predicted classes
        """
        proba = self.predict_proba(X)
        return (proba > 0.5).astype(int)
    
    def save_model(self, path: str) -> None:
        """Save model to disk"""
        if self.model is None:
            raise ValueError("No model to save")
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save Keras model
        self.model.save(path)
        
        # Save scaler and metadata separately
        import joblib
        metadata_path = str(path).replace('.h5', '_metadata.joblib')
        joblib.dump({
            'feature_cols': self.feature_cols,
            'scaler': self.scaler,
            'sequence_length': self.sequence_length,
            'params': {
                'lstm_units': self.lstm_units,
                'dropout_rate': self.dropout_rate,
                'learning_rate': self.learning_rate
            }
        }, metadata_path)
        
        logger.info(f"LSTM model saved to {path}")
    
    @classmethod
    def load_model(cls, path: str) -> 'LSTMPredictor':
        """Load model from disk"""
        import joblib
        
        # Load Keras model
        model = keras.models.load_model(path)
        
        # Load metadata
        metadata_path = str(path).replace('.h5', '_metadata.joblib')
        metadata = joblib.load(metadata_path)
        
        predictor = cls(**metadata['params'])
        predictor.model = model
        predictor.feature_cols = metadata['feature_cols']
        predictor.scaler = metadata['scaler']
        predictor.sequence_length = metadata['sequence_length']
        predictor.is_trained = True
        
        return predictor
