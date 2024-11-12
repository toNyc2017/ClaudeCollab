# Build frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Build backend
FROM python:3.9-slim as backend-build
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# Final stage
FROM python:3.9-slim
WORKDIR /app

# Copy built frontend
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Copy backend
COPY --from=backend-build /app/backend /app/backend

WORKDIR /app/backend
EXPOSE 8000

CMD ["python", "app.py"]