# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for Python and Quart
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN apt update && apt install -y git
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port your Quart app will run on
EXPOSE 8258

# Set the command to run the Quart app with Uvicorn
CMD ["python", "agent.py", "--host", "0.0.0.0"]
