#!/bin/bash
set -e

# Script para generar una CA propia y firmar certificados para OpenLDAP
# Uso: ./gen-certs.sh

CERT_DIR="$(dirname "$0")"
LDAP_CERT_DIR="${CERT_DIR}/ldap-cert"

mkdir -p "${LDAP_CERT_DIR}"

echo "==> Generando clave privada de la CA..."
openssl genrsa -out "${CERT_DIR}/ca-key.pem" 4096

echo "==> Generando certificado autofirmado de la CA (válido 10 años)..."
openssl req -x509 -new -nodes \
  -key "${CERT_DIR}/ca-key.pem" \
  -sha256 -days 3650 \
  -out "${CERT_DIR}/ca-cert.pem" \
  -subj "/C=CL/ST=Santiago/L=Santiago/O=MiOrg/OU=Seguridad/CN=Mi CA Interna"

echo "==> Generando clave privada para el servidor LDAP..."
openssl genrsa -out "${LDAP_CERT_DIR}/ldap-key.pem" 2048

echo "==> Generando CSR para el servidor LDAP..."
openssl req -new \
  -key "${LDAP_CERT_DIR}/ldap-key.pem" \
  -out "${LDAP_CERT_DIR}/ldap.csr" \
  -subj "/C=CL/ST=Santiago/L=Santiago/O=MiOrg/OU=Infraestructura/CN=openldap"

echo "==> Firmando certificado del servidor con la CA..."
openssl x509 -req \
  -in "${LDAP_CERT_DIR}/ldap.csr" \
  -CA "${CERT_DIR}/ca-cert.pem" \
  -CAkey "${CERT_DIR}/ca-key.pem" \
  -CAcreateserial \
  -out "${LDAP_CERT_DIR}/ldap-cert.pem" \
  -days 825 -sha256 \
  -extfile <(printf "subjectAltName=DNS:openldap,DNS:localhost,IP:127.0.0.1")

echo "==> Ajustando permisos..."
chmod 644 "${CERT_DIR}/ca-cert.pem"
chmod 644 "${LDAP_CERT_DIR}/ldap-cert.pem"
chmod 600 "${LDAP_CERT_DIR}/ldap-key.pem"

echo "==> Certificados generados correctamente en ${CERT_DIR}"
echo ""
echo "Archivos:"
echo "  CA Cert: ${CERT_DIR}/ca-cert.pem"
echo "  LDAP Cert: ${LDAP_CERT_DIR}/ldap-cert.pem"
echo "  LDAP Key: ${LDAP_CERT_DIR}/ldap-key.pem"
