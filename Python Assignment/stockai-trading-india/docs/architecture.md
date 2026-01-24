# Architecture of the AI Trading Tool

## Overview
The AI Trading Tool is designed for real-time trading in the Indian stock market. It integrates various components to facilitate data ingestion, strategy execution, and broker communication, ensuring a seamless trading experience.

## Components

### 1. Main Application
- **File:** `src/app.py`
- **Description:** Sets up the main application logic, integrating data ingestion, strategy execution, and broker communication.

### 2. Data Ingestion
- **Files:**
  - `src/data/ingest.py`: Responsible for ingesting market data from various sources.
  - `src/data/loader.py`: Loads historical and real-time data for analysis and strategy execution.
  - `src/data/sources.py`: Defines the data sources used for trading, including APIs and data feeds.

### 3. Trading Strategies
- **Files:**
  - `src/strategies/base.py`: Defines a base class for trading strategies, providing a common interface.
  - `src/strategies/example_strategy.py`: Implements an example trading strategy for customization.

### 4. Machine Learning Models
- **Files:**
  - `src/models/train.py`: Contains functions for training machine learning models on historical data.
  - `src/models/predict.py`: Functions for making predictions using trained models.

### 5. Real-Time Operations
- **Files:**
  - `src/realtime/streamer.py`: Handles real-time data streaming and updates.
  - `src/realtime/order_manager.py`: Manages order execution and tracking in real-time.

### 6. Broker Integration
- **Files:**
  - `src/broker/zerodha_adapter.py`: Implements the interface for interacting with the Zerodha trading platform.

### 7. Utilities
- **Files:**
  - `src/utils/logger.py`: Provides logging functionality for tracking events and errors.
  - `src/utils/helpers.py`: Contains utility functions for various tasks.

### 8. Data Schemas
- **File:** `src/schemas/types.py`
- **Description:** Defines data schemas and types used throughout the application.

## Deployment
- **Files:**
  - `Dockerfile`: Defines the Docker image for the application.
  - `docker-compose.yml`: Configures services for running the application in a Docker environment.
  - `scripts/deploy.sh`: Shell script for deploying the application.

## Testing
- **Files:**
  - `tests/test_strategies.py`: Unit tests for trading strategies.
  - `tests/test_broker.py`: Unit tests for broker integration.

## Notebooks
- **Files:**
  - `notebooks/eda.ipynb`: Jupyter notebook for exploratory data analysis.
  - `notebooks/model_experiments.ipynb`: Jupyter notebook for experimenting with machine learning models.

## Configuration
- **File:** `configs/default.yaml`
- **Description:** Contains default configuration settings for the application.

## Conclusion
This architecture provides a comprehensive framework for developing an AI trading tool tailored for the Indian stock market, ensuring efficient data handling, strategy execution, and real-time trading capabilities.