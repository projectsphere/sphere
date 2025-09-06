#!/bin/bash

set -e

DOCKER_IMAGE="spherebot"
CONTAINER_NAME="spherebot"

echo "Pulling the latest code from Git..."
git pull origin main

echo "Building the Docker image..."
docker build -t $DOCKER_IMAGE .

if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "Stopping the existing container..."
    docker stop $CONTAINER_NAME
fi

if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    echo "Removing the existing container..."
    docker rm $CONTAINER_NAME
fi

echo "Running the new container..."
docker run -d \
  --name $CONTAINER_NAME \
  -v /host/path/data:/app/data \
  -v /host/path/logs:/app/logs \
  $DOCKER_IMAGE

echo "Deployment complete."
