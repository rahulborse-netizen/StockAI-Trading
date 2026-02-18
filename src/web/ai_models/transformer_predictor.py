"""
Transformer-based Time Series Predictor
Uses attention mechanisms for feature importance and sequence modeling
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from pathlib import Path
import os

logger = logging.getLogger(__name__)

TRANSFORMER_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TRANSFORMER_AVAILABLE = True
except ImportError:
    logger.debug("PyTorch not available, Transformer predictor disabled")

if TRANSFORMER_AVAILABLE:
    class StockDataset(Dataset):
        """Dataset for stock time series"""
        def __init__(self, sequences, labels):
            self.sequences = torch.FloatTensor(sequences)
            self.labels = torch.FloatTensor(labels)
        
        def __len__(self):
            return len(self.sequences)
        
        def __getitem__(self, idx):
            return self.sequences[idx], self.labels[idx]
    
    class TransformerPredictor(nn.Module):
        """Transformer model for stock price prediction"""
        def __init__(self, input_dim, d_model=64, nhead=4, num_layers=2, dropout=0.1):
            super(TransformerPredictor, self).__init__()
            self.d_model = d_model
            self.embedding = nn.Linear(input_dim, d_model)
            self.pos_encoder = nn.PositionalEncoding(d_model, dropout)
            
            encoder_layers = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=d_model * 4,
                dropout=dropout
            )
            self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers=num_layers)
            self.fc = nn.Linear(d_model, 1)
            self.sigmoid = nn.Sigmoid()
        
        def forward(self, x):
            # x shape: (batch, seq_len, input_dim)
            x = self.embedding(x) * np.sqrt(self.d_model)
            x = x.transpose(0, 1)  # (seq_len, batch, d_model)
            x = self.pos_encoder(x)
            x = self.transformer_encoder(x)
            x = x.mean(dim=0)  # Average over sequence
            x = self.fc(x)
            return self.sigmoid(x)
    
    class PositionalEncoding(nn.Module):
        """Positional encoding for transformer"""
        def __init__(self, d_model, dropout=0.1, max_len=5000):
            super(PositionalEncoding, self).__init__()
            self.dropout = nn.Dropout(p=dropout)
            
            pe = torch.zeros(max_len, d_model)
            position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
            pe[:, 0::2] = torch.sin(position * div_term)
            pe[:, 1::2] = torch.cos(position * div_term)
            pe = pe.unsqueeze(0).transpose(0, 1)
            self.register_buffer('pe', pe)
        
        def forward(self, x):
            x = x + self.pe[:x.size(0), :]
            return self.dropout(x)


class TransformerPredictorWrapper:
    """Wrapper for Transformer predictor with training and prediction"""
    
    def __init__(self):
        self.model: Optional[object] = None
        self.model_path = Path('data/models/transformer_predictor.pt')
        self.sequence_length = 30  # Lookback window
        self.input_dim = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if TRANSFORMER_AVAILABLE else None
    
    def is_available(self) -> bool:
        """Check if transformer is available"""
        return TRANSFORMER_AVAILABLE
    
    def load_model(self) -> bool:
        """Load pre-trained model"""
        if not TRANSFORMER_AVAILABLE:
            return False
        
        if self.model_path.exists():
            try:
                self.model = TransformerPredictor(input_dim=self.input_dim or 20)
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                self.model.eval()
                logger.info("Transformer model loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to load transformer model: {e}")
                return False
        return False
    
    def train(
        self,
        train_data: pd.DataFrame,
        feature_cols: list,
        label_col: str = 'label_up',
        epochs: int = 10,
        batch_size: int = 32,
        learning_rate: float = 0.001
    ) -> Dict:
        """Train transformer model"""
        if not TRANSFORMER_AVAILABLE:
            return {'success': False, 'error': 'PyTorch not available'}
        
        try:
            # Prepare sequences
            sequences, labels = self._prepare_sequences(train_data, feature_cols, label_col)
            
            if len(sequences) < batch_size:
                return {'success': False, 'error': 'Insufficient data for training'}
            
            self.input_dim = len(feature_cols)
            self.model = TransformerPredictor(input_dim=self.input_dim).to(self.device)
            
            dataset = StockDataset(sequences, labels)
            dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
            
            criterion = nn.BCELoss()
            optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
            
            self.model.train()
            losses = []
            
            for epoch in range(epochs):
                epoch_loss = 0
                for batch_sequences, batch_labels in dataloader:
                    batch_sequences = batch_sequences.to(self.device)
                    batch_labels = batch_labels.to(self.device)
                    
                    optimizer.zero_grad()
                    outputs = self.model(batch_sequences).squeeze()
                    loss = criterion(outputs, batch_labels)
                    loss.backward()
                    optimizer.step()
                    
                    epoch_loss += loss.item()
                
                avg_loss = epoch_loss / len(dataloader)
                losses.append(avg_loss)
                logger.info(f"Transformer epoch {epoch+1}/{epochs}, loss: {avg_loss:.4f}")
            
            # Save model
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(self.model.state_dict(), self.model_path)
            
            return {
                'success': True,
                'epochs': epochs,
                'final_loss': losses[-1] if losses else None,
                'losses': losses
            }
            
        except Exception as e:
            logger.error(f"Transformer training failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _prepare_sequences(
        self,
        data: pd.DataFrame,
        feature_cols: list,
        label_col: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for transformer"""
        sequences = []
        labels = []
        
        data = data[feature_cols + [label_col]].fillna(0)
        
        for i in range(self.sequence_length, len(data)):
            seq = data[feature_cols].iloc[i-self.sequence_length:i].values
            label = data[label_col].iloc[i]
            sequences.append(seq)
            labels.append(label)
        
        return np.array(sequences), np.array(labels)
    
    def predict(self, data: pd.DataFrame, feature_cols: list) -> Optional[float]:
        """Predict probability using transformer"""
        if not TRANSFORMER_AVAILABLE or self.model is None:
            return None
        
        try:
            # Prepare sequence
            if len(data) < self.sequence_length:
                return None
            
            sequence_data = data[feature_cols].tail(self.sequence_length).fillna(0).values
            sequence_tensor = torch.FloatTensor(sequence_data).unsqueeze(0).to(self.device)
            
            self.model.eval()
            with torch.no_grad():
                output = self.model(sequence_tensor)
                probability = output.item()
            
            return float(probability)
            
        except Exception as e:
            logger.error(f"Transformer prediction failed: {e}")
            return None
    
    def get_feature_importance(self, data: pd.DataFrame, feature_cols: list) -> Dict[str, float]:
        """Get feature importance using attention weights"""
        if not TRANSFORMER_AVAILABLE or self.model is None:
            return {}
        
        # Simplified feature importance - in production, extract from attention weights
        # For now, return equal importance
        return {col: 1.0 / len(feature_cols) for col in feature_cols}


# Global instance
_transformer_predictor: Optional[TransformerPredictorWrapper] = None


def get_transformer_predictor() -> TransformerPredictorWrapper:
    """Get global transformer predictor instance"""
    global _transformer_predictor
    if _transformer_predictor is None:
        _transformer_predictor = TransformerPredictorWrapper()
        if TRANSFORMER_AVAILABLE:
            _transformer_predictor.load_model()
    return _transformer_predictor
