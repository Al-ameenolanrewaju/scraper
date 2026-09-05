FROM node:20-slim

# Install Python 3 and Pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
COPY requirements.txt ./

RUN npm install
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
RUN npm install -g pm2

COPY . .

EXPOSE 8080

CMD ["pm2-runtime", "start", "ecosystem.config.js"]