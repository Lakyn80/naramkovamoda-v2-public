FROM node:20-alpine AS deps

WORKDIR /app

COPY frontend/admin/package.json frontend/admin/package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /app

ENV NEXT_PUBLIC_API_BASE=/api
ENV NMM_BACKEND_URL=http://backend:5050

COPY --from=deps /app/node_modules ./node_modules
COPY frontend/admin . 

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_PUBLIC_API_BASE=/api
ENV NMM_BACKEND_URL=http://backend:5050

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next

EXPOSE 3001

CMD ["npm", "run", "start", "--", "-p", "3001"]
