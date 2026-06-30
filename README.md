# Rate Limiter Service (`rate-limiter`)

A lightweight, high-performance microservice built with **Python and FastAPI** designed to enforce traffic throttling policies across the Flagship ecosystem. It utilizes an asynchronous **Redis-backed Sliding Window Log** algorithm to compute quota consumption states with minimal overhead.

All further description is from perspective of it being a part of [Flagship Platform](https://github.com/NGUgeneral/flagship-platform). But it does not mean that it can't be used as standalone service as-is without any issues. 

## Core Architecture & Strategy Logic

The service is entirely stateless and exposes a uniform endpoint (`POST /api/v1/is_allowed`). It deterministically isolates traffic patterns inside Redis using key namespacing based on the presence of a cryptographically verified token:

1. **Token-Based Strategy (Main):** Triggered when an explicit `client_key` is supplied. It expects dynamic `limit` and `window` metrics determined by the upstream service. To prevent silent SLA degradation, this contract fails fast (`400 Bad Request`) if limit parameters are omitted.
2. **IP-Based Strategy (Fallback):** Triggered for anonymous edge traffic. It tracks the client's public IP address and gracefully falls back to secure infrastructure-wide defaults configured via environment variables.

Under the hood, evaluation is executed atomically inside Redis via a server-time sliding window Lua script, eliminating clock-drift bugs across distributed compute workers.

## API Routing Contract (v0.1)

All routes are explicitly namespaced to the application prefix layer.

### Intranet Evaluation Channel
* **`POST /api/v1/is_allowed`** — Accepts an execution payload matching client identification tokens and returns a deterministic access status.
  `.`.`.json
  {
    "status": "allowed",
    "current_count": 14,
    "limit": 100,
    "remaining": 86
  }
  `.`.`.

### Restricted Infrastructure Logs (IP Whitelisted at Gateway)
* **`GET /api/v1/docs`** — Interactive Swagger UI documentation page.
* **`GET /api/v1/health`** — Simple JSON readiness state check confirming standalone Redis availability.

### Isolated Local Development Loop
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

## Configuration Parameters
* `REDIS_URL`: Storage string referencing the target cache instance (e.g., `redis://redis-cache:6379/0`).
* `DEFAULT_IP_LIMIT`: Fallback volume quota configuration per evaluation window frame.
* `DEFAULT_IP_WINDOW`: Duration tracking size parsed in seconds.
