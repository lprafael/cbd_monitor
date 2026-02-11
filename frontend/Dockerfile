# Dockerfile para el frontend de CBD Monitor
FROM node:18-alpine AS build

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY package*.json ./

# Instalar dependencias
# Usar npm install en lugar de npm ci para mayor flexibilidad
RUN npm install --legacy-peer-deps

# Copiar el resto del código
COPY . .

# Argumento para la URL de la API (con valor por defecto)
ARG REACT_APP_API_URL=http://172.16.222.222:5001
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Compilar la aplicación
RUN npm run build

# Etapa de producción con nginx
# ... (etapa de producción)
FROM nginx:alpine

# 1. Copiamos el build a una carpeta con el nombre del sistema
COPY --from=build /app/build /usr/share/nginx/html/cbd_monitor

# 2. También copiamos el index a la raíz para que la IP funcione
RUN cp /usr/share/nginx/html/cbd_monitor/index.html /usr/share/nginx/html/index.html

# 3. Copiamos la configuración de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]