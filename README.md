# rate-limiter

Very basic, but pretty robust implementation of Distributed Rate Limiter.
To start the project locally:
docker-compose up build

To develop the project
Navigate to project directory and pen 2 terminals
docker-compose up redis -d
uvicorn main:app --reload
