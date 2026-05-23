# Production build for Cloud Run.
# Local dev uses Dockerfile.dev (referenced from docker-compose.yml).
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Baked into the static bundle. Change + rebuild if the backend URL changes.
ENV REACT_APP_API_URL=https://api.cadence-dash.com
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
