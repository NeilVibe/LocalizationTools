"""
EMB-001: Auto-build embeddings+index on TM upload - Unit Tests

Tests the automatic indexing service that triggers after TM upload.
"""

import pytest
from unittest.mock import Mock, patch


class TestSchemaUpdate:
    """Test that TMUploadResponse includes indexing_status."""

    def test_tm_upload_response_has_indexing_status(self):
        """Verify TMUploadResponse schema has indexing_status field."""
        from server.tools.ldm.schemas.tm import TMUploadResponse
        
        # Check field exists
        assert "indexing_status" in TMUploadResponse.model_fields
        
        # Check it's optional
        field = TMUploadResponse.model_fields["indexing_status"]
        assert field.default is None
        
        # Test instantiation
        response = TMUploadResponse(
            tm_id=1,
            name="Test TM",
            entry_count=100,
            status="ready",
            time_seconds=5.0,
            rate_per_second=20,
            indexing_status="scheduled"
        )
        assert response.indexing_status == "scheduled"
        
        # Test without indexing_status
        response2 = TMUploadResponse(
            tm_id=1,
            name="Test TM",
            entry_count=100,
            status="ready",
            time_seconds=5.0,
            rate_per_second=20
        )
        assert response2.indexing_status is None


class TestServiceExports:
    """Test that services module exports correctly."""

    def test_services_module_exports(self):
        """Verify services/__init__.py exports indexing functions."""
        from server.tools.ldm.services import (
            trigger_auto_indexing,
            trigger_auto_indexing_async,
            check_indexing_needed,
        )
        
        # All should be callable
        assert callable(trigger_auto_indexing)
        assert callable(trigger_auto_indexing_async)
        assert callable(check_indexing_needed)


class TestRouteIntegration:
    """Test that tm_crud.py has correct integration."""

    def test_upload_tm_has_background_tasks(self):
        """Verify upload_tm endpoint has BackgroundTasks parameter."""
        from server.tools.ldm.routes.tm_crud import upload_tm
        import inspect
        
        sig = inspect.signature(upload_tm)
        params = list(sig.parameters.keys())
        
        # Should have background_tasks parameter
        assert "background_tasks" in params
        
        # Should have auto_index parameter
        assert "auto_index" in params

    def test_upload_tm_imports_indexing_service(self):
        """Verify tm_crud.py imports trigger_auto_indexing."""
        import server.tools.ldm.routes.tm_crud as tm_crud_module
        
        # Should have trigger_auto_indexing available
        assert hasattr(tm_crud_module, 'trigger_auto_indexing')

    def test_background_tasks_import(self):
        """Verify BackgroundTasks is imported in tm_crud."""
        from server.tools.ldm.routes.tm_crud import BackgroundTasks
        from fastapi import BackgroundTasks as FastAPIBackgroundTasks
        
        # Should be the FastAPI BackgroundTasks
        assert BackgroundTasks is FastAPIBackgroundTasks


class TestIndexingServiceFunctions:
    """Test indexing service function signatures."""

    def test_trigger_auto_indexing_signature(self):
        """Verify trigger_auto_indexing has correct signature."""
        from server.tools.ldm.services.indexing_service import trigger_auto_indexing
        import inspect
        
        sig = inspect.signature(trigger_auto_indexing)
        params = list(sig.parameters.keys())
        
        # Should have these parameters
        assert "tm_id" in params
        assert "user_id" in params
        assert "username" in params
        assert "silent" in params
        
        # silent should default to True
        assert sig.parameters["silent"].default == True

    def test_trigger_auto_indexing_async_signature(self):
        """Verify trigger_auto_indexing_async has correct signature."""
        from server.tools.ldm.services.indexing_service import trigger_auto_indexing_async
        import inspect
        
        sig = inspect.signature(trigger_auto_indexing_async)
        params = list(sig.parameters.keys())
        
        # Should have same parameters as sync version
        assert "tm_id" in params
        assert "user_id" in params
        assert "username" in params
        assert "silent" in params
        
        # Should be an async function
        assert inspect.iscoroutinefunction(trigger_auto_indexing_async)

    def test_check_indexing_needed_signature(self):
        """Verify check_indexing_needed has correct signature."""
        from server.tools.ldm.services.indexing_service import check_indexing_needed
        import inspect
        
        sig = inspect.signature(check_indexing_needed)
        params = list(sig.parameters.keys())
        
        # Should have tm_id parameter
        assert "tm_id" in params
        
        # Should return bool annotation
        assert sig.return_annotation == bool
