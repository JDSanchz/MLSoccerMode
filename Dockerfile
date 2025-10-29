# Ubuntu base so we can apt-install ttyd easily
FROM ubuntu:22.04

# System deps + Python + ttyd
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip python3-venv ttyd ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# App setup
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .

# Render provides PORT; fall back for local runs
ENV PORT=10000 \
    PYTHONUNBUFFERED=1 \
    TTYD_CRED=admin:change-me

EXPOSE 10000

# Start ttyd serving your Python CLI
# -p uses $PORT (Render injects it)
# -c enables HTTP Basic Auth (user:pass)
# -t title customizes the page title
CMD sh -c "exec ttyd -p ${PORT} -c ${TTYD_CRED} -t title='MLSoccerMode' python3 main.py"
