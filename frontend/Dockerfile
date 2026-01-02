# Frontend Dockerfile
FROM node:20-alpine as build

WORKDIR /app

# Копирование package файлов
COPY package*.json ./

# Установка зависимостей
RUN npm ci

# Копирование исходного кода
COPY . .

# Передача переменных окружения в build stage
# Render.com передает переменные окружения, которые доступны как ARG во время сборки
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL:-http://localhost:5001/api}

# Сборка приложения (Vite подхватит VITE_API_URL из ENV)
RUN npm run build

# Production stage
FROM nginx:alpine

# Копирование собранного приложения
COPY --from=build /app/dist /usr/share/nginx/html

# Копирование конфигурации nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

