# Relay Node

This is a lightweight relay service designed to transmit structured payloads between dynamic endpoints using minimal protocol overhead.

It supports basic POST, GET, and DELETE operations for flexible session-based message passing.

---

## Features

- Stateless by design
- In-memory session routing
- Session-isolated data streams
- Compatible with any JSON-based client
- Suitable for prototyping or ephemeral communication

---

## API Overview

### `POST /sessions/{session}/{id}`
Submit a data packet to a session.

### `GET /sessions/{session}`
Retrieve all data packets for a session.

### `DELETE /sessions/{session}/{id}`
Remove a data packet after processing.

---

## Deployment

This service can be deployed using Python 3 and FastAPI.

### Local Run
```bash
uvicorn server:app --host 0.0.0.0 --port 10000