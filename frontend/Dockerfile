# NOVA 프론트엔드: 빌드한 정적 파일을 nginx 로 서빙하고 /api 는 백엔드로 넘깁니다
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# 같은 주소의 /api 로 부르므로 API 주소는 비워 둡니다
ARG VITE_API_BASE=""
ARG VITE_USE_MOCK=false
ARG VITE_SHOW_DEMO=true
ENV VITE_API_BASE=$VITE_API_BASE \
    VITE_USE_MOCK=$VITE_USE_MOCK \
    VITE_SHOW_DEMO=$VITE_SHOW_DEMO
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
