# MarketSpot 프론트엔드 (개발용 Vite 서버). 소스는 compose 에서 볼륨 마운트.
# node_modules 는 이미지에서 npm ci 로 설치하고 익명 볼륨으로 보존한다
# (호스트 macOS 바이너리가 컨테이너를 덮어쓰지 않도록).
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

EXPOSE 4000

# --host 0.0.0.0: 컨테이너 밖(호스트 브라우저)에서 접근 가능하게.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
