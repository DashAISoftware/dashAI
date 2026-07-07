# Stage 1: build frontend static assets
FROM node:22-alpine AS frontend
WORKDIR /app/DashAI/front
COPY DashAI/front/ ./
RUN corepack enable && yarn install --frozen-lockfile && yarn build

# Stage 2: Python backend serving the built frontend
FROM python:3.11-slim
WORKDIR /app
COPY . .
COPY --from=frontend /app/DashAI/front/build DashAI/front/build
RUN pip install --no-cache-dir -r requirements-cpu.txt && \
    pip install --no-cache-dir --no-deps -e .
ENV DASHAI_HOST=0.0.0.0
EXPOSE 8000
CMD ["python", "-m", "DashAI", "--no-browser"]
