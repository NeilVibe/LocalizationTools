"""
Routing Repositories.

These repositories transparently route requests based on entity IDs:
- Negative IDs → SQLite OFFLINE mode (local Electron data)
- Positive IDs → Primary repository (PostgreSQL or SQLite SERVER mode)

Routes never need to know about negative ID handling.
"""

from server.repositories.routing.row_repo import RoutingRowRepository

__all__ = ["RoutingRowRepository"]
