#!/usr/bin/env bash

TOKEN=$(curl -s -X POST http://localhost:5001/token \
  -H 'Content-Type: application/json' \
  -d '{"user":"alice","roles":["operator"]}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo $TOKEN

# Calcular firma HMAC
BODY='{"status":"delivered"}'
HMAC_SECRET="demo-hmac-secret"
CLIENT_ID="test-client"
CID=$(uuidgen)

SIG=$(printf %s "$BODY" | openssl dgst -sha256 -hmac "$HMAC_SECRET" -r | awk '{print $1}')
echo "SIG=${SIG}"

# Gateway URL
GATEWAY_URL="https://localhost:5000"

# Petición exitosa
curl -ki --insecure \
  -X PUT "$GATEWAY_URL/orders/ABC123/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Correlation-Id: $CID" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "X-Body-Signature: $SIG" \
  --data "$BODY"

# Token inválido - 401
curl -ki --insecure \
  -X PUT "$GATEWAY_URL/orders/ABC123/status" \
  -H "Authorization: Bearer badtoken" \
  -H "Content-Type: application/json" \
  -H "X-Correlation-Id: $CID" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "X-Body-Signature: $SIG" \
  --data "$BODY"

# Firma inválida - 401
curl -ki --insecure \
  -X PUT "$GATEWAY_URL/orders/ABC123/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Correlation-Id: $CID" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "X-Body-Signature: badsig" \
  --data "$BODY"
  