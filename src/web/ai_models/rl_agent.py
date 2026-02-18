"""
Reinforcement Learning Agent for Position Management
Uses policy gradient methods (PPO) for optimal entry/exit decisions
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from pathlib import Path
from collections import deque
import os

logger = logging.getLogger(__name__)

RL_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    RL_AVAILABLE = True
except ImportError:
    logger.debug("PyTorch not available, RL agent disabled")

if RL_AVAILABLE:
    class PolicyNetwork(nn.Module):
        """Policy network for RL agent"""
        def __init__(self, state_dim, action_dim, hidden_dim=128):
            super(PolicyNetwork, self).__init__()
            self.fc1 = nn.Linear(state_dim, hidden_dim)
            self.fc2 = nn.Linear(hidden_dim, hidden_dim)
            self.fc3 = nn.Linear(hidden_dim, action_dim)
            self.softmax = nn.Softmax(dim=-1)
        
        def forward(self, state):
            x = F.relu(self.fc1(state))
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return self.softmax(x)
    
    class ValueNetwork(nn.Module):
        """Value network for RL agent"""
        def __init__(self, state_dim, hidden_dim=128):
            super(ValueNetwork, self).__init__()
            self.fc1 = nn.Linear(state_dim, hidden_dim)
            self.fc2 = nn.Linear(hidden_dim, hidden_dim)
            self.fc3 = nn.Linear(hidden_dim, 1)
        
        def forward(self, state):
            x = F.relu(self.fc1(state))
            x = F.relu(self.fc2(x))
            return self.fc3(x)


class RLAgent:
    """
    Reinforcement Learning Agent for Trading
    Learns optimal position management strategies
    """
    
    def __init__(self):
        self.state_dim = 10  # State features: price, volume, indicators, etc.
        self.action_dim = 3  # Actions: HOLD, BUY, SELL
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if RL_AVAILABLE else None
        
        if RL_AVAILABLE:
            self.policy_net = PolicyNetwork(self.state_dim, self.action_dim).to(self.device)
            self.value_net = ValueNetwork(self.state_dim).to(self.device)
            self.optimizer_policy = optim.Adam(self.policy_net.parameters(), lr=0.0003)
            self.optimizer_value = optim.Adam(self.value_net.parameters(), lr=0.001)
        
        self.model_path = Path('data/models/rl_agent.pt')
        self.memory = deque(maxlen=10000)  # Experience replay buffer
        self.gamma = 0.99  # Discount factor
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        
    def is_available(self) -> bool:
        """Check if RL is available"""
        return RL_AVAILABLE
    
    def load_model(self) -> bool:
        """Load pre-trained RL agent"""
        if not RL_AVAILABLE:
            return False
        
        if self.model_path.exists():
            try:
                checkpoint = torch.load(self.model_path, map_location=self.device)
                self.policy_net.load_state_dict(checkpoint['policy'])
                self.value_net.load_state_dict(checkpoint['value'])
                self.epsilon = checkpoint.get('epsilon', self.epsilon_min)
                logger.info("RL agent loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to load RL agent: {e}")
                return False
        return False
    
    def get_state(self, data: pd.DataFrame, current_price: float) -> np.ndarray:
        """Extract state features from market data"""
        if len(data) < 20:
            return np.zeros(self.state_dim)
        
        # Calculate features
        returns = data['close'].pct_change().tail(10).values
        volume = data['volume'].tail(10).values / data['volume'].mean() if 'volume' in data.columns else np.zeros(10)
        
        # Technical indicators
        sma_10 = data['close'].tail(10).mean()
        sma_20 = data['close'].tail(20).mean() if len(data) >= 20 else sma_10
        
        # Normalize features
        state = np.array([
            (current_price - sma_10) / sma_10,  # Price vs SMA10
            (current_price - sma_20) / sma_20 if sma_20 > 0 else 0,  # Price vs SMA20
            returns.mean(),  # Average return
            returns.std(),  # Volatility
            volume.mean(),  # Average volume
            (current_price - data['close'].iloc[-1]) / data['close'].iloc[-1],  # Recent change
            data['close'].tail(5).max() / current_price - 1,  # Recent high
            data['close'].tail(5).min() / current_price - 1,  # Recent low
            len([r for r in returns if r > 0]) / len(returns) if len(returns) > 0 else 0.5,  # Win rate
            data['close'].iloc[-1] / data['close'].iloc[0] - 1 if len(data) > 0 else 0  # Trend
        ])
        
        # Pad or truncate to state_dim
        if len(state) < self.state_dim:
            state = np.pad(state, (0, self.state_dim - len(state)))
        elif len(state) > self.state_dim:
            state = state[:self.state_dim]
        
        return state
    
    def select_action(self, state: np.ndarray, training: bool = False) -> int:
        """Select action using policy network"""
        if not RL_AVAILABLE:
            return 1  # Default: HOLD
        
        # Epsilon-greedy exploration
        if training and np.random.random() < self.epsilon:
            return np.random.randint(0, self.action_dim)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        self.policy_net.eval()
        with torch.no_grad():
            action_probs = self.policy_net(state_tensor)
            action = action_probs.argmax().item()
        
        return action
    
    def calculate_reward(
        self,
        action: int,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        target: float,
        sharpe_ratio: float = 0.0
    ) -> float:
        """
        Calculate reward based on action and outcome
        Reward function optimized for Sharpe ratio
        """
        if action == 0:  # HOLD
            # Small negative reward for holding (opportunity cost)
            return -0.01
        
        elif action == 1:  # BUY
            if current_price <= stop_loss:
                return -1.0  # Stop loss hit
            elif current_price >= target:
                return 1.0  # Target hit
            else:
                # Reward proportional to progress toward target
                progress = (current_price - entry_price) / (target - entry_price)
                return progress * 0.5
        
        else:  # SELL
            if current_price >= stop_loss:  # For shorts, stop loss is above
                return -1.0
            elif current_price <= target:
                return 1.0
            else:
                progress = (entry_price - current_price) / (entry_price - target)
                return progress * 0.5
    
    def train_step(self, batch_size: int = 32) -> Dict:
        """Train RL agent on experience replay buffer"""
        if not RL_AVAILABLE or len(self.memory) < batch_size:
            return {'success': False, 'error': 'Insufficient experience'}
        
        try:
            # Sample batch
            batch = np.random.choice(len(self.memory), batch_size, replace=False)
            states, actions, rewards, next_states, dones = zip(*[self.memory[i] for i in batch])
            
            states = torch.FloatTensor(np.array(states)).to(self.device)
            actions = torch.LongTensor(actions).to(self.device)
            rewards = torch.FloatTensor(rewards).to(self.device)
            next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
            dones = torch.FloatTensor(dones).to(self.device)
            
            # Calculate returns
            returns = []
            G = 0
            for reward, done in zip(reversed(rewards), reversed(dones)):
                G = reward + self.gamma * G * (1 - done)
                returns.insert(0, G)
            returns = torch.FloatTensor(returns).to(self.device)
            
            # Update value network
            values = self.value_net(states).squeeze()
            value_loss = F.mse_loss(values, returns)
            self.optimizer_value.zero_grad()
            value_loss.backward()
            self.optimizer_value.step()
            
            # Update policy network (PPO-style)
            action_probs = self.policy_net(states)
            advantages = returns - values.detach()
            
            # Policy gradient
            log_probs = torch.log(action_probs.gather(1, actions.unsqueeze(1)).squeeze() + 1e-8)
            policy_loss = -(log_probs * advantages).mean()
            
            self.optimizer_policy.zero_grad()
            policy_loss.backward()
            self.optimizer_policy.step()
            
            # Decay epsilon
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            
            return {
                'success': True,
                'value_loss': value_loss.item(),
                'policy_loss': policy_loss.item(),
                'epsilon': self.epsilon
            }
            
        except Exception as e:
            logger.error(f"RL training failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def save_model(self):
        """Save RL agent"""
        if not RL_AVAILABLE:
            return
        
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                'policy': self.policy_net.state_dict(),
                'value': self.value_net.state_dict(),
                'epsilon': self.epsilon
            }, self.model_path)
            logger.info("RL agent saved successfully")
        except Exception as e:
            logger.error(f"Failed to save RL agent: {e}")
    
    def get_position_recommendation(
        self,
        data: pd.DataFrame,
        current_price: float,
        entry_price: Optional[float] = None
    ) -> Dict:
        """Get position management recommendation"""
        state = self.get_state(data, current_price)
        action = self.select_action(state, training=False)
        
        action_names = ['HOLD', 'BUY', 'SELL']
        
        return {
            'action': action_names[action],
            'confidence': 0.7,  # Simplified - would use action probabilities
            'state_features': state.tolist()
        }


# Global instance
_rl_agent: Optional[RLAgent] = None


def get_rl_agent() -> RLAgent:
    """Get global RL agent instance"""
    global _rl_agent
    if _rl_agent is None:
        _rl_agent = RLAgent()
        if RL_AVAILABLE:
            _rl_agent.load_model()
    return _rl_agent
