FROM node:20-slim

# Install Python 3, Pip, system Chromium, and required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    chromium \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Tell Puppeteer to use the system-installed Chromium binary
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Copy dependency files first to leverage Docker layer caching
COPY package*.json ./
COPY requirements.txt ./

# Install Node modules and Python packages
RUN npm install
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Install PM2 globally to manage dual processes
RUN npm install -g pm2

# Copy all application source code
COPY . .

EXPOSE 8080

# Launch Python and Node services using PM2
CMD ["pm2-runtime", "start", "ecosystem.config.js"]