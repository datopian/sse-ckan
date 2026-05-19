"""Tests for CKAN RPC Action Service.

Tests cover single actions, batch operations, action discovery, and error handling
using CKAN's standard testing patterns.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from google.protobuf import json_format, struct_pb2

from ckan.logic import NotAuthorized, NotFound, ValidationError, get_action
from ckan.rpc.service.action_service import CkanActionServiceImpl
from ckan.rpc.proto import ckan_rpc_pb2
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import grpc


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestCkanActionService:
    """Test cases for CkanActionService with integration testing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = CkanActionServiceImpl()
        self.mock_grpc_context = Mock()

    def _create_action_request(
        self,
        action: str,
        user: str = None,
        data: dict = None
    ) -> ckan_rpc_pb2.ActionRequest:
        """Helper to create ActionRequest messages."""
        request = ckan_rpc_pb2.ActionRequest()
        request.action = action

        if user or data:
            request.context.user = user or ""
            request.context.api_version = 3

        if data:
            request.data.CopyFrom(
                json_format.ParseDict(data, struct_pb2.Struct())
            )

        return request

    def test_execute_action_package_list_success(self):
        """Test successful package_list action execution."""
        # Execute
        request = self._create_action_request('package_list')
        response = self.service.ExecuteAction(request, self.mock_grpc_context)

        # Assert
        assert response.success is True
        assert response.error.type == ""
        assert 'result' in json_format.MessageToDict(response.result)

    def test_execute_action_package_create_success(self):
        """Test successful package_create action execution with real DB."""
        # Setup
        user = factories.User()

        # Create action request
        request = self._create_action_request(
            'package_create',
            user=user['name'],
            data={'name': 'test-dataset', 'title': 'Test Dataset'}
        )

        # Execute
        response = self.service.ExecuteAction(request, self.mock_grpc_context)

        # Assert
        assert response.success is True
        result = json_format.MessageToDict(response.result)
        assert result['name'] == 'test-dataset'
        assert result['title'] == 'Test Dataset'

        # Verify package was actually created in DB
        pkg = helpers.call_action('package_show', id=result['id'])
        assert pkg['name'] == 'test-dataset'

    def test_execute_action_not_found(self):
        """Test action not found error."""
        # Setup
        request = self._create_action_request('nonexistent_action_xyz')

        # Execute
        mock_context = Mock()
        mock_context.set_code = Mock()
        mock_context.set_details = Mock()
        response = self.service.ExecuteAction(request, mock_context)

        # Assert
        assert response.success is False
        assert response.error.type == "NotFound"
        mock_context.set_code.assert_called_once()

    def test_execute_action_validation_error(self):
        """Test validation error handling with missing required fields."""
        # Setup - try to create package without name (required field)
        request = self._create_action_request(
            'package_create',
            user='admin',
            data={'description': 'test'}  # name is missing
        )

        # Execute
        mock_context = Mock()
        mock_context.set_code = Mock()
        mock_context.set_details = Mock()
        response = self.service.ExecuteAction(request, mock_context)

        # Assert
        assert response.success is False
        assert response.error.type == "ValidationError"
        mock_context.set_code.assert_called_once()

    def test_execute_action_auth_error_anonymous(self):
        """Test authorization error handling for anonymous user trying to create."""
        # Setup - anonymous user trying to create package (not authorized)
        request = self._create_action_request(
            'package_create',
            user=None,  # anonymous
            data={'name': 'test-dataset'}
        )

        # Execute
        mock_context = Mock()
        mock_context.set_code = Mock()
        mock_context.set_details = Mock()
        response = self.service.ExecuteAction(request, mock_context)

        # Assert
        assert response.success is False
        assert response.error.type == "NotAuthorized"
        mock_context.set_code.assert_called_once()

    def test_execute_batch_success(self):
        """Test batch action execution with multiple package_list calls."""
        # Setup
        request = ckan_rpc_pb2.BatchActionRequest()
        request.requests.append(self._create_action_request('package_list'))
        request.requests.append(self._create_action_request('user_list'))
        request.requests.append(self._create_action_request('organization_list'))
        request.stop_on_error = False

        # Execute
        response = self.service.ExecuteBatch(request, self.mock_grpc_context)

        # Assert
        assert len(response.responses) == 3
        assert response.all_succeeded is True
        assert response.failed_count == 0
        # All should be successful
        for resp in response.responses:
            assert resp.success is True

    def test_execute_batch_with_error_stop(self):
        """Test batch execution stops on first error."""
        # Setup
        request = ckan_rpc_pb2.BatchActionRequest()
        request.requests.append(self._create_action_request('package_list'))
        request.requests.append(
            self._create_action_request('package_create', data={})  # Invalid
        )
        request.requests.append(self._create_action_request('user_list'))
        request.stop_on_error = True

        # Execute
        response = self.service.ExecuteBatch(request, self.mock_grpc_context)

        # Assert
        assert response.failed_count >= 1  # Second request should fail
        assert response.responses[0].success is True
        assert response.responses[1].success is False
        # Verify stop_on_error behavior
        assert response.all_succeeded is False

    def test_list_actions(self):
        """Test listing available actions."""
        # Execute
        request = ckan_rpc_pb2.ActionListRequest()
        response = self.service.ListActions(request, Mock())

        # Assert
        assert isinstance(response, ckan_rpc_pb2.ActionListResponse)
        assert response.total >= 0
        # Check that common actions are present
        action_names = [action.name for action in response.actions]
        assert any('package' in name for name in action_names)

    def test_list_actions_with_category_filter(self):
        """Test listing actions with category filter."""
        # Execute
        request = ckan_rpc_pb2.ActionListRequest()
        request.category = 'package'
        response = self.service.ListActions(request, Mock())

        # Assert
        assert response.total >= 0
        # All returned actions should be package-related
        for action in response.actions:
            assert 'package' in action.name

    def test_list_actions_with_search_filter(self):
        """Test listing actions with search filter."""
        # Execute
        request = ckan_rpc_pb2.ActionListRequest()
        request.search = 'create'
        response = self.service.ListActions(request, Mock())

        # Assert
        # All returned actions should contain 'create'
        for action in response.actions:
            assert 'create' in action.name.lower()

    @patch('ckan.rpc.service.action_service.get_action')
    def test_get_action_info(self, mock_get_action):
        """Test getting action information."""
        # Setup
        mock_action = Mock()
        mock_action.__doc__ = "Test action for creating packages"
        mock_action.side_effect_free = False
        mock_get_action.return_value = mock_action

        request = ckan_rpc_pb2.GetActionRequest()
        request.action_name = 'package_create'

        # Execute
        response = self.service.GetAction(request, Mock())

        # Assert
        assert response.name == 'package_create'
        assert response.side_effect_free is False

    @patch('ckan.rpc.service.action_service.get_action')
    def test_get_action_not_found(self, mock_get_action):
        """Test getting non-existent action."""
        # Setup
        mock_get_action.side_effect = NotFound("Action not found")

        request = ckan_rpc_pb2.GetActionRequest()
        request.action_name = 'nonexistent_action'

        # Execute
        mock_context = Mock()
        mock_context.set_code = Mock()
        mock_context.set_details = Mock()
        response = self.service.GetAction(request, mock_context)

        # Assert
        mock_context.set_code.assert_called_once()

    @patch('ckan.rpc.service.action_service.get_action')
    def test_execute_stream(self, mock_get_action):
        """Test streaming action execution."""
        # Setup
        mock_action = Mock(return_value={'id': f'test-{i}'} for i in range(3))
        mock_get_action.return_value = mock_action

        requests = [
            self._create_action_request('action1'),
            self._create_action_request('action2'),
            self._create_action_request('action3'),
        ]

        # Execute
        responses = list(self.service.ExecuteStream(iter(requests), Mock()))

        # Assert
        assert len(responses) == 3
        assert all(r.success is True for r in responses)

    @patch('ckan.rpc.service.action_service.get_action')
    def test_struct_conversion(self, mock_get_action):
        """Test protobuf Struct conversion."""
        # Setup
        test_data = {
            'name': 'test-dataset',
            'description': 'A test dataset',
            'tags': [{'name': 'test'}],
            'extras': {'custom': 'value'}
        }

        mock_action = Mock(return_value=test_data)
        mock_get_action.return_value = mock_action

        request = self._create_action_request('package_create', data=test_data)

        # Execute
        response = self.service.ExecuteAction(request, Mock())

        # Assert
        assert response.success is True
        result_dict = json_format.MessageToDict(response.result)
        assert result_dict['name'] == 'test-dataset'
        assert result_dict['description'] == 'A test dataset'

    def test_context_building(self):
        """Test CKAN context building from RPC context."""
        # Setup
        action_context = ckan_rpc_pb2.ActionContext()
        action_context.user = 'testuser'
        action_context.api_version = 3
        action_context.extras['custom_key'] = 'custom_value'

        # Execute
        context = self.service._build_context(action_context)

        # Assert
        assert context['user'] == 'testuser'
        assert context['api_version'] == 3
        assert context['custom_key'] == 'custom_value'

    def test_error_response_building_validation(self):
        """Test building error response for validation errors."""
        # Setup
        error = ValidationError({'field1': ['Error 1', 'Error 2']})

        # Execute
        error_response = self.service._build_error_response(error, 'test_action')

        # Assert
        assert error_response.type == 'ValidationError'
        assert 'field1' in error_response.field_errors

    def test_error_response_building_generic(self):
        """Test building error response for generic errors."""
        # Setup
        error = Exception("Something went wrong")

        # Execute
        error_response = self.service._build_error_response(error, 'test_action')

        # Assert
        assert error_response.type == 'Exception'
        assert error_response.message == "Something went wrong"


@pytest.mark.usefixtures('clean_db', 'with_request_context')
class TestActionServiceIntegration:
    """Integration tests for action service with real CKAN operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = CkanActionServiceImpl()
        self.mock_grpc_context = Mock()

    def _create_action_request(
        self,
        action: str,
        user: str = None,
        data: dict = None
    ) -> ckan_rpc_pb2.ActionRequest:
        """Helper to create ActionRequest messages."""
        request = ckan_rpc_pb2.ActionRequest()
        request.action = action

        if user or data:
            request.context.user = user or ""
            request.context.api_version = 3

        if data:
            request.data.CopyFrom(
                json_format.ParseDict(data, struct_pb2.Struct())
            )

        return request

    def test_package_create_and_show(self):
        """Test creating a package and retrieving it via RPC."""
        # Setup
        user = factories.User()

        # Create package via RPC
        create_request = self._create_action_request(
            'package_create',
            user=user['name'],
            data={
                'name': 'integration-test-package',
                'title': 'Integration Test Package',
                'notes': 'Test package for RPC integration'
            }
        )

        # Execute create
        create_response = self.service.ExecuteAction(create_request, self.mock_grpc_context)
        assert create_response.success is True

        created_pkg = json_format.MessageToDict(create_response.result)
        pkg_id = created_pkg['id']

        # Show package via RPC
        show_request = self._create_action_request(
            'package_show',
            data={'id': pkg_id}
        )

        # Execute show
        show_response = self.service.ExecuteAction(show_request, self.mock_grpc_context)
        assert show_response.success is True

        shown_pkg = json_format.MessageToDict(show_response.result)
        assert shown_pkg['name'] == 'integration-test-package'
        assert shown_pkg['title'] == 'Integration Test Package'

    def test_package_search(self):
        """Test searching for packages via RPC."""
        # Setup - create some packages
        user = factories.User()
        factories.Dataset(creator_user_id=user['id'], name='dataset-one', title='First Dataset')
        factories.Dataset(creator_user_id=user['id'], name='dataset-two', title='Second Dataset')

        # Search via RPC
        request = self._create_action_request(
            'package_search',
            data={'q': 'dataset', 'rows': 10}
        )

        # Execute
        response = self.service.ExecuteAction(request, self.mock_grpc_context)

        # Assert
        assert response.success is True
        result = json_format.MessageToDict(response.result)
        assert result['count'] >= 2

    def test_resource_create_in_package(self):
        """Test creating a resource in a package via RPC."""
        # Setup
        user = factories.User()

        # Create package
        pkg_request = self._create_action_request(
            'package_create',
            user=user['name'],
            data={'name': 'resource-test-pkg'}
        )
        pkg_response = self.service.ExecuteAction(pkg_request, self.mock_grpc_context)
        pkg_id = json_format.MessageToDict(pkg_response.result)['id']

        # Create resource in package
        res_request = self._create_action_request(
            'resource_create',
            user=user['name'],
            data={
                'package_id': pkg_id,
                'url': 'https://example.com/data.csv',
                'name': 'Test Resource',
                'format': 'CSV'
            }
        )

        # Execute
        res_response = self.service.ExecuteAction(res_request, self.mock_grpc_context)

        # Assert
        assert res_response.success is True
        resource = json_format.MessageToDict(res_response.result)
        assert resource['name'] == 'Test Resource'
        assert resource['format'] == 'CSV'
        assert resource['package_id'] == pkg_id

    def test_batch_read_operations(self):
        """Test batch operations reading multiple entity types."""
        # Setup
        factories.User()
        factories.Organization()
        factories.Dataset()

        # Batch request with multiple read operations
        batch_request = ckan_rpc_pb2.BatchActionRequest()
        batch_request.requests.append(self._create_action_request('user_list'))
        batch_request.requests.append(self._create_action_request('organization_list'))
        batch_request.requests.append(self._create_action_request('package_list'))
        batch_request.stop_on_error = False

        # Execute
        response = self.service.ExecuteBatch(batch_request, self.mock_grpc_context)

        # Assert
        assert response.all_succeeded is True
        assert response.failed_count == 0
        assert len(response.responses) == 3
