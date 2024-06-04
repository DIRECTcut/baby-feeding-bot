# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8443 available to the world outside this container
EXPOSE 8443

# Define environment variable
ENV NAME BreastFeedingBot

# Run bot.py when the container launches
CMD ["python", "bot.py"]
