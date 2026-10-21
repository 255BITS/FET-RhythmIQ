# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Patch trust before pip, Git, or SDK downloads (eMudhra incident, 2026-10-20).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && sed -i \
        -e 's|^mozilla/emSign_ECC_Root_CA_-_G3.crt|!&|' \
        -e 's|^mozilla/Comodo_AAA_Services_root.crt|!&|' \
        /etc/ca-certificates.conf \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# PIP_CERT replaces pip's vendored trust, including on legacy Python 3.9.
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

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
