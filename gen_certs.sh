#!/usr/bin/env bash
set -e
mkdir -p certs
cd certs

# CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 \
  -out ca.crt -subj "/CN=Local Test CA"

# Server (gateway)
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=gateway"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256

# Client (para curl/postman)
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=client1"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt -days 365 -sha256

echo "Listo: certs/ca.crt, server.crt/key y client.crt/key"
