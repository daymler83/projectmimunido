FROM python:3.8

# Instalar dependencias del sistema necesarias para compilar librerías
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libatlas-base-dev \
    gfortran

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt primero
COPY requirements.txt /app/requirements.txt

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código al contenedor
COPY . /app

# Exponer el puerto que usa la aplicación
EXPOSE 5000

# Ejecutar la aplicación
CMD ["python", "app.py"]
