FROM node:20-slim

# Install Python 3, Pip, Chromium, and required Linux fonts/libraries
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    chromium \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    --no-install-recommends \
    && rm -rf /var/lib/apt-get/lists/*

# Set Environment variables for Puppeteer
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Copy dependency configs first
COPY package*.json ./
COPY requirements.txt ./

# Install Node and Python packages
RUN npm install
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install process manager globally
RUN npm install -g pm2

EXPOSE 8080

# Launch both services via PM2
CMD ["pm2-runtime", "start", "ecosystem.config.js"]