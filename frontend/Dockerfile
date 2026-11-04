# 1단계: Vue 앱 빌드 (결과물: /app/dist)
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY public/ public/
COPY src/ src/
RUN npm run build

# 2단계: nginx로 빌드 결과 제공 + /api/ 프록시
FROM nginx:1.27-alpine

# 백엔드 주소 (host:port). Docker Desktop에서 호스트의 uvicorn에 붙을 때 기본값 사용
ENV BACKEND_UPSTREAM=host.docker.internal:8000

COPY nginx/templates/ /etc/nginx/templates/
COPY --from=build /app/dist/ /usr/share/nginx/html/

EXPOSE 80
