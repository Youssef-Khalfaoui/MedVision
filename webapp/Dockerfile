# Use an official Node.js image
FROM node:22-alpine

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# npm ci installs exactly what package-lock.json pins (reproducible builds)
RUN npm ci

# Copy the rest of the application code
COPY . .

# Build the React app for production
RUN npm run build

# Expose the port Vite preview runs on
EXPOSE 4173

# Non-root: this container only serves static files and proxies /api
RUN chown -R node:node /app
USER node

# Command to run the app
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0"]
