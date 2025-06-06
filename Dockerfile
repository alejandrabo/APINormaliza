# Usa una imagen base de Python con herramientas necesarias
FROM python:3.10-slim

# Evita prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependencias del sistema necesarias para compilar libpostal
RUN apt-get update && apt-get install -y \
    curl autoconf automake libtool pkg-config build-essential \
    git python3-dev && \
    apt-get clean

# Clona e instala libpostal
RUN git clone https://github.com/openvenues/libpostal && \
    cd libpostal && \
    ./bootstrap.sh && \
    ./configure --datadir=/usr/local/share/libpostal && \
    make -j4 && \
    make install && \
    ldconfig

# Crea carpeta de la app
WORKDIR /app

# Copia los archivos del proyecto
COPY . .

# Instala dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto de la API Flask
EXPOSE 5000

# Comando para ejecutar la app
CMD ["python", "app.py"]

