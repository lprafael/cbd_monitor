# Dockerfile para el frontend de CBD Monitor
FROM node:18-alpine as build

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
FROM nginx:alpine

# Copiar los archivos compilados al directorio de nginx
COPY --from=build /app/build /usr/share/nginx/html

# Copiar configuración personalizada de nginx (opcional)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer el puerto 80
EXPOSE 80

# Comando para iniciar nginx
CMD ["nginx", "-g", "daemon off;"]
