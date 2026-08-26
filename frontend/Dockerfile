FROM node:24-alpine

WORKDIR /app

# Dockerized frontends share a Compose network with the backend service. Keep
# local host development's Vite fallback separate from the container default.
ENV VITE_API_PROXY_TARGET=http://backend:8000

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
