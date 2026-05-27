#!/bin/bash
set -e

# Gera secrets.toml a partir das variáveis de ambiente definidas no HF Space
mkdir -p /code/.streamlit

cat > /code/.streamlit/secrets.toml << EOF
[gdrive]
vendas_id = "${GDRIVE_VENDAS_ID}"
meta_id   = "${GDRIVE_META_ID}"

[users.comercial1]
email  = "comercial1@acocearense.com.br"
name   = "Comercial 1"
role   = "comercial"
hash   = "${HASH_COMERCIAL1}"

[users.comercial2]
email  = "comercial2@acocearense.com.br"
name   = "Comercial 2"
role   = "comercial"
hash   = "${HASH_COMERCIAL2}"

[users.planejamento]
email  = "planejamento@acocearense.com.br"
name   = "Planejamento"
role   = "planejamento"
hash   = "${HASH_PLANEJAMENTO}"
EOF

# Inicia o Streamlit na porta 7860 (padrão HF Spaces)
streamlit run app/dashboard.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
