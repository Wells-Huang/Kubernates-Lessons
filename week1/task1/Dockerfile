FROM --platform=$TARGETPLATFORM node:20-slim

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

COPY server.js ./

EXPOSE 3000

CMD ["node", "server.js"]
