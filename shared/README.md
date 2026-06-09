# Shared

This directory contains shared code used across multiple services in the Home Telemetry workspace.

It is the common layer for pieces that services need to communicate consistently and avoid duplicating core logic.

## What lives here

- `schemas/`: shared data and database-related schemas used by services to validate and exchange structured data.
- `logger/`: shared logging implementation and configuration so all services emit logs in a consistent format.
- `tests/`: tests for shared module to ensure the common building blocks remain stable.

## Why this exists

Keeping these components in one place helps all services:

- speak the same data language,
- share observability patterns,
- and reduce drift between implementations.
