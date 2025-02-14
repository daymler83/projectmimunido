# Use Python 3.9 as base image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file to the correct path
COPY requirements.txt /app/projects/mimunido/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/projects/mimunido/requirements.txt


# Copy the rest of the application files to the project folder
COPY . /app/projects/mimunido

# Expose the port Flask will run on
EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "projects.mimunido.app_new_adj_up:app"]
