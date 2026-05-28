FROM python:3.10-slim

WORKDIR /code

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o app e configuração de tema
COPY app/ ./app/
COPY .streamlit/config.toml ./.streamlit/config.toml

# Script de inicialização
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 7860

CMD ["./start.sh"]
