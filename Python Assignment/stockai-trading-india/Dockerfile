FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/
COPY notebooks/ ./notebooks/
COPY docs/ ./docs/

# Expose the necessary port (if applicable)
# EXPOSE 5000

# Command to run the application
CMD ["python", "src/main.py"]