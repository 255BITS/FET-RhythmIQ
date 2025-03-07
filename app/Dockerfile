# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for Python and Quart
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Uvicorn (if it's not already in your requirements.txt)
RUN pip install uvicorn

# Copy the rest of the application code
COPY app/ . 
COPY common /common

# Expose the port your Quart app will run on
EXPOSE 8257

# Set the command to run the Quart app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8257"]
