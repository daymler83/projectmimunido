# Usa una imagen base oficial de Python
FROM python:3.8

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia todos los archivos de tu proyecto al contenedor
COPY . /app

# Instala las dependencias usando requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto 5000 (o el que uses)
EXPOSE 5000

# Comando para ejecutar tu aplicación
CMD ["python", "app.py"]
 
