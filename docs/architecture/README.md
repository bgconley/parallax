# Architecture

Parallax uses an API-first backend with thin FastAPI routes, application services for domain rules, repositories for persistence, and adapters for external systems. Domain rules must not depend on FastAPI, database clients, or workflow SDKs.
