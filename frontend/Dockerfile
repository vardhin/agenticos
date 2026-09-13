FROM oven/bun:1 AS build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build:budget
EXPOSE 4173
CMD ["bun", "run", "preview", "--host", "0.0.0.0", "--port", "4173"]
