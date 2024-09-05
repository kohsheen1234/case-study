# Use the official Node.js 20 image
FROM node:20

# Skip Puppeteer's default Chromium download since we'll use Google Chrome
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD true

# Install dependencies and Google Chrome Stable
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    --no-install-recommends \
  && curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list' \
  && apt-get update \
  && apt-get install -y \
    google-chrome-stable \
    --no-install-recommends \
  && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json to the container
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy the rest of the application code to the container
COPY . .

# Run the application as the non-root `node` user
USER node

# Command to start the Node.js application
CMD ["node", "src/index.js"]
