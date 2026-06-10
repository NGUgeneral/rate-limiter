# Distributed Rate Limiter

A stateless, high-performance, and decoupled Distributed Rate Limiter built with FastAPI and backed by AWS Lambda (via Mangum) and Upstash Redis. 

It acts as an out-of-band sentinel for the entire ecosystem, enforcing business tier SLAs for authenticated traffic and protecting public endpoints from DDoS or scraping floods.

## 🚀 Core Architecture & Strategy Logic

The service is entirely stateless and exposes a uniform endpoint (`POST /v1/is_allowed`). It deterministically isolates traffic patterns inside Redis using key namespacing based on the presence of a cryptographically verified token:

1. **Token-Based Strategy (Main):** Triggered when an explicit `client_key` is supplied. It expects dynamic `limit` and `window` metrics determined by the upstream service. To prevent silent SLA degradation, this contract fails fast (`400 Bad Request`) if limit parameters are omitted.
2. **IP-Based Strategy (Fallback):** Triggered for anonymous edge traffic. It tracks the client's public IP address and gracefully falls back to secure infrastructure-wide defaults configured via environment variables.

Under the hood, evaluation is executed atomically inside Redis via a server-time sliding window Lua script, eliminating clock-drift bugs across distributed compute workers.

---

## 🛠️ Local Development & Orchestration

Dependencies are cleanly isolated to minimize the deployment artifact footprint on AWS Lambda (`requirements-dev.txt` extends production rules to append local development tools like `uvicorn` and `pytest`).

### 1. Initial Setup
Create your local environment file:
```bash
cp .env.example .env
```

Ensure your .env contains valid credentials:
```Ini, TOML
REDIS_URL=redis://localhost:6379
DEFAULT_IP_LIMIT=100
DEFAULT_IP_WINDOW=60
```

### 2. Spinning up the Ecosystem (Full Docker Build)
To spin up the rate limiter container alongside local data dependencies in a single unified terminal:
```bash
docker-compose up --build
```

### 3. Isolated Local Development Loop
If you want to edit Python files natively with hot-reloading active on your local machine:

1. **Start the background data layer:**
   ```bash
   docker-compose up local-redis -d
   ```
2. **Activate your environment & install dev dependencies:**
    ```bash
    source venv/bin/activate
    pip install -r requirements-dev.txt
    ```
3. **Fire up the hot-reloading server:**
    ```bash
    uvicorn main:app --reload --port 8000
    ```

## 📖 API Documentation
Interactive OpenAPI/Swagger documentation, schema constraints, and mock request payloads are accessible locally at:
* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`
