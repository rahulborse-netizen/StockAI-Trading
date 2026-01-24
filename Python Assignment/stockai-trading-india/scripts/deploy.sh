#!/bin/bash

# Deploy script for the AI trading tool in the Indian stock market

# Set environment variables
export $(cat .env | xargs)

# Build the Docker image
docker build -t stockai-trading-india .

# Run the Docker container
docker run -d --name stockai-trading-india-container \
  -e API_KEY=$API_KEY \
  -e API_SECRET=$API_SECRET \
  -p 5000:5000 \
  stockai-trading-india

echo "Deployment completed. The trading tool is now running."