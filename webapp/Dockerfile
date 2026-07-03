# Stage 1: Сборка Vue приложения
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Подставляем API URL при сборке
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Nginx для раздачи статики
FROM nginx:alpine

# Копируем собранные файлы
COPY --from=build /app/dist /usr/share/nginx/html

# Копируем конфиг nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
