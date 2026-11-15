# Estágio 1: gera os arquivos estáticos
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Estágio 2: serve o build com Nginx
FROM nginx:alpine
# As configurações ficam fora do conf.d; o 40-https.sh escolhe quais ativar ao iniciar (#23)
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/ /etc/nginx/proto1/
COPY --chmod=755 nginx/40-https.sh /docker-entrypoint.d/40-https.sh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80 443
