FROM nginx:1.27-alpine

# 백엔드 주소 (host:port). Docker Desktop에서 호스트의 uvicorn에 붙을 때 기본값 사용
ENV BACKEND_UPSTREAM=host.docker.internal:8000

COPY nginx/templates/ /etc/nginx/templates/
COPY index.html login.html signup.html mypage.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

EXPOSE 80
