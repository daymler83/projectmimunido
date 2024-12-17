# Usa Python 3.8 como imagen base
FROM python:3.8

# Instalar dependencias del sistema necesarias para numpy y pandas
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    libatlas-base-dev \
    libssl-dev \
    libffi-dev \
    python3-dev \
    wget \
    && apt-get clean

# Actualizar pip
RUN python -m pip install --upgrade pip

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt
COPY requirements.txt /app/requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos del proyecto
COPY . /app

# Exponer el puerto 5000
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
