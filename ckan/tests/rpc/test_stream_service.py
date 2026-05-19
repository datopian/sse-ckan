"""Tests for CKAN RPC Stream Service.

Tests cover streaming of packages, resources, and activity data.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from google.protobuf import timestamp_pb2

from ckan.model import Package, Resource, Activity
from ckan.rpc.service.stream_service import CkanStreamServiceImpl
from ckan.rpc.proto import ckan_rpc_pb2
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.usefixtures('clean_db', 'with_request_context')
class TestCkanStreamService:
    """Test cases for CkanStreamService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = CkanStreamServiceImpl()
        self.mock_context = Mock()

    def test_stream_packages_empty(self):
        """Test streaming with no packages."""
        # Setup
        request = ckan_rpc_pb2.PackageStreamRequest()
        mock_context = Mock()

        # Mock the Session query
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.__iter__.return_value = iter([])
            mock_session.query.return_value = mock_query

            # Execute
            responses = list(self.service.StreamPackages(request, mock_context))

            # Assert
            assert len(responses) == 0

    def test_stream_packages_with_filter(self):
        """Test streaming packages with organization filter."""
        # Setup
        request = ckan_rpc_pb2.PackageStreamRequest()
        request.organization_id = 'test-org'
        mock_context = Mock()

        # Mock the Session query
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.__iter__.return_value = iter([])
            mock_session.query.return_value = mock_query

            # Execute
            responses = list(self.service.StreamPackages(request, mock_context))

            # Assert
            # Verify filter was called
            assert mock_query.filter.called

    def test_stream_packages_with_timestamp_filter(self):
        """Test streaming packages since specific timestamp."""
        # Setup
        request = ckan_rpc_pb2.PackageStreamRequest()
        ts = timestamp_pb2.Timestamp()
        ts.GetCurrentTime()
        request.since.CopyFrom(ts)
        mock_context = Mock()

        # Mock the Session query
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.__iter__.return_value = iter([])
            mock_session.query.return_value = mock_query

            # Execute
            responses = list(self.service.StreamPackages(request, mock_context))

            # Assert
            # Verify timestamp filter was applied
            assert mock_query.filter.called

    def test_stream_resources_empty(self):
        """Test streaming with no resources."""
        # Setup
        request = ckan_rpc_pb2.ResourceStreamRequest()
        mock_context = Mock()

        # Mock the Session query
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.__iter__.return_value = iter([])
            mock_session.query.return_value = mock_query

            # Execute
            responses = list(self.service.StreamResources(request, mock_context))

            # Assert
            assert len(responses) == 0

    def test_stream_resources_with_package_filter(self):
        """Test streaming resources by package."""
        # Setup
        request = ckan_rpc_pb2.ResourceStreamRequest()
        request.package_id = 'test-package'
        mock_context = Mock()

        # Mock the Session query
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.__iter__.return_value = iter([])
            mock_session.query.return_value = mock_query

            # Execute
            responses = list(self.service.StreamResources(request, mock_context))

            # Assert
            assert mock_query.filter.called

    def test_stream_activity_empty(self):
        """Test streaming activity with no entries."""
        # Setup
        request = ckan_rpc_pb2.ActivityStreamRequest()
        mock_context = Mock()

        # Mock the Session query
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.__iter__.return_value = iter([])
            mock_session.query.return_value = mock_query

            # Execute
            responses = list(self.service.StreamActivity(request, mock_context))

            # Assert
            assert len(responses) == 0

    def test_stream_activity_with_user_filter(self):
        """Test streaming activity for specific user."""
        # Setup
        request = ckan_rpc_pb2.ActivityStreamRequest()
        request.user_id = 'test-user'
        mock_context = Mock()

        # Mock the Session query
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.__iter__.return_value = iter([])
            mock_session.query.return_value = mock_query

            # Execute
            responses = list(self.service.StreamActivity(request, mock_context))

            # Assert
            assert mock_query.filter.called

    def test_package_to_proto_conversion(self):
        """Test converting Package model to protobuf."""
        # Setup
        mock_package = Mock(spec=Package)
        mock_package.id = 'test-id'
        mock_package.name = 'test-package'
        mock_package.title = 'Test Package'
        mock_package.notes = 'A test package'
        mock_package.state = 'active'
        mock_package.resources = []
        mock_package.groups = []
        mock_package.metadata_created = datetime.now()
        mock_package.metadata_modified = datetime.now()

        # Execute
        proto_package = self.service._package_to_proto(mock_package)

        # Assert
        assert proto_package.id == 'test-id'
        assert proto_package.name == 'test-package'
        assert proto_package.title == 'Test Package'
        assert proto_package.notes == 'A test package'
        assert proto_package.state == 'active'

    def test_resource_to_proto_conversion(self):
        """Test converting Resource model to protobuf."""
        # Setup
        mock_resource = Mock(spec=Resource)
        mock_resource.id = 'res-id'
        mock_resource.package_id = 'pkg-id'
        mock_resource.url = 'http://example.com/data.csv'
        mock_resource.format = 'CSV'
        mock_resource.description = 'Test data'
        mock_resource.name = 'data'
        mock_resource.hash = 'abc123'
        mock_resource.size = 1024
        mock_resource.created = datetime.now()
        mock_resource.last_modified = datetime.now()

        # Execute
        proto_resource = self.service._resource_to_proto(mock_resource)

        # Assert
        assert proto_resource.id == 'res-id'
        assert proto_resource.package_id == 'pkg-id'
        assert proto_resource.url == 'http://example.com/data.csv'
        assert proto_resource.format == 'CSV'
        assert proto_resource.description == 'Test data'
        assert proto_resource.size == 1024

    def test_activity_to_proto_conversion(self):
        """Test converting Activity model to protobuf."""
        # Setup
        mock_activity = Mock(spec=Activity)
        mock_activity.id = 'act-id'
        mock_activity.user_id = 'user-id'
        mock_activity.object_id = 'pkg-id'
        mock_activity.activity_type = 'created package'
        mock_activity.timestamp = datetime.now()
        mock_activity.data = '{"key": "value"}'

        # Execute
        proto_activity = self.service._activity_to_proto(mock_activity)

        # Assert
        assert proto_activity.id == 'act-id'
        assert proto_activity.user_id == 'user-id'
        assert proto_activity.object_id == 'pkg-id'
        assert proto_activity.activity_type == 'created package'

    def test_stream_error_handling(self):
        """Test error handling in streaming."""
        # Setup
        request = ckan_rpc_pb2.PackageStreamRequest()
        mock_context = Mock()
        mock_context.set_code = Mock()
        mock_context.set_details = Mock()

        # Mock the Session query to raise an error
        with patch('ckan.rpc.service.stream_service.Session') as mock_session:
            mock_session.query.side_effect = Exception("Database error")

            # Execute
            responses = list(self.service.StreamPackages(request, mock_context))

            # Assert
            assert mock_context.set_code.called
            assert mock_context.set_details.called


@pytest.mark.usefixtures('clean_db', 'with_request_context')
class TestStreamServiceIntegration:
    """Integration tests for stream service with real data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = CkanStreamServiceImpl()
        self.mock_context = Mock()

    def test_stream_real_packages(self):
        """Test streaming real packages from database."""
        # Setup - create some packages
        user = factories.User()
        pkg1 = factories.Dataset(creator_user_id=user['id'], name='stream-pkg-1')
        pkg2 = factories.Dataset(creator_user_id=user['id'], name='stream-pkg-2')

        # Stream packages
        request = ckan_rpc_pb2.PackageStreamRequest()
        packages = list(self.service.StreamPackages(request, self.mock_context))

        # Assert - should have at least the 2 created packages
        assert len(packages) >= 2
        package_names = [p.name for p in packages]
        assert 'stream-pkg-1' in package_names
        assert 'stream-pkg-2' in package_names

    def test_stream_packages_with_organization_filter(self):
        """Test streaming packages filtered by organization."""
        # Setup
        user = factories.User()
        org = factories.Organization()
        pkg = factories.Dataset(
            creator_user_id=user['id'],
            owner_org=org['id'],
            name='org-filtered-pkg'
        )

        # Stream packages for specific organization
        request = ckan_rpc_pb2.PackageStreamRequest()
        request.organization_id = org['id']
        packages = list(self.service.StreamPackages(request, self.mock_context))

        # Assert
        assert len(packages) >= 1
        package_names = [p.name for p in packages]
        assert 'org-filtered-pkg' in package_names

    def test_stream_real_resources(self):
        """Test streaming real resources from database."""
        # Setup - create a package with resources
        user = factories.User()
        pkg = factories.Dataset(creator_user_id=user['id'])
        res1 = factories.Resource(package_id=pkg['id'], name='resource-1', format='CSV')
        res2 = factories.Resource(package_id=pkg['id'], name='resource-2', format='JSON')

        # Stream resources
        request = ckan_rpc_pb2.ResourceStreamRequest()
        resources = list(self.service.StreamResources(request, self.mock_context))

        # Assert
        assert len(resources) >= 2
        resource_names = [r.name for r in resources]
        assert 'resource-1' in resource_names
        assert 'resource-2' in resource_names

    def test_stream_resources_by_package(self):
        """Test streaming resources filtered by package."""
        # Setup
        user = factories.User()
        pkg = factories.Dataset(creator_user_id=user['id'])
        res = factories.Resource(package_id=pkg['id'], name='pkg-specific-resource')

        # Stream resources for specific package
        request = ckan_rpc_pb2.ResourceStreamRequest()
        request.package_id = pkg['id']
        resources = list(self.service.StreamResources(request, self.mock_context))

        # Assert
        assert len(resources) >= 1
        resource_names = [r.name for r in resources]
        assert 'pkg-specific-resource' in resource_names
