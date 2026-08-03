# Thrive Causemetics — Launch Intelligence Hub
# Zero-dependency static server: no npm install needed at build time.
FROM node:20-alpine

WORKDIR /app
COPY . .

ENV NODE_ENV=production
# Railway injects PORT dynamically; 8080 is the local/default fallback.
EXPOSE 8080

CMD ["node", "server.js"]
