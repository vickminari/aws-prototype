#!/bin/sh
# Roda a cada início do container (docker-entrypoint.d da imagem nginx), antes do Nginx.
# Escolhe a configuração conforme o certificado do Let's Encrypt exista (#23):
#   sem certificado → http.conf (aplicação por HTTP, permite emitir o certificado)
#   com certificado → https.conf + http-redirect.conf (HTTP redireciona para HTTPS)
set -eu

CERT=/etc/letsencrypt/live/proto1/fullchain.pem
SRC=/etc/nginx/proto1
DEST=/etc/nginx/conf.d

rm -f "${DEST}"/*.conf

if [ -f "${CERT}" ]; then
  cp "${SRC}/https.conf" "${SRC}/http-redirect.conf" "${DEST}/"
  echo "$0: certificado encontrado; HTTPS ativo e HTTP redirecionando"
  # O certbot renova o arquivo, mas o Nginx só usa o novo depois de um reload
  (while :; do sleep 21600; nginx -s reload; done) &
else
  cp "${SRC}/http.conf" "${DEST}/"
  echo "$0: sem certificado; servindo só HTTP"
fi
