"""Memory Engine domain layer.

Holds domain concepts, invariants, value objects and domain errors.

Boundary rule (plan 8.1 section 7): modules in this package must not import
FastAPI, database drivers, SQLAlchemy, RabbitMQ/Celery, object-storage SDKs,
HTTP clients, or ``memory_engine.infrastructure``. The rule is enforced by
``tests/memory_engine/unit/test_domain_boundary.py``.

Phase 8.1 provides only domain errors. Domain models arrive with Phase 8.2.
"""
