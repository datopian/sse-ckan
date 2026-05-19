"""
CKAN Action RPC Service Implementation

This module implements the CkanActionService gRPC interface, providing
RPC access to all CKAN actions with support for batch operations and
action introspection.
"""

import logging
import json
from typing import Dict, Any, Iterator, Optional, List
from concurrent.futures import ThreadPoolExecutor

import grpc
from google.protobuf import json_format, struct_pb2

from ckan.logic import get_action, NotAuthorized, NotFound, ValidationError
from ckan.model import User
from ckan.lib.helpers import helper_functions
from ckan.authz import is_authorized

from ..proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc

log = logging.getLogger(__name__)


class CkanActionServiceImpl(ckan_rpc_pb2_grpc.CkanActionServiceServicer):
    """
    gRPC service implementation for CKAN actions.

    This service provides RPC access to all CKAN actions with support for:
    - Single action execution
    - Batch operations
    - Action introspection and discovery
    - Streaming operations
    """

    def __init__(self):
        """Initialize the action service."""
        self._action_cache: Dict[str, Any] = {}
        self._load_action_cache()

    def _load_action_cache(self) -> None:
        """Load and cache all available actions for quick access."""
        try:
            # Import action modules
            from ckan.logic import action

            # Get all action functions
            for action_module in ['get', 'create', 'update', 'delete', 'patch']:
                module = __import__(
                    f'ckan.logic.action.{action_module}',
                    fromlist=['*']
                )
                for name in dir(module):
                    obj = getattr(module, name)
                    if callable(obj) and not name.startswith('_'):
                        self._action_cache[name] = obj
        except Exception as e:
            log.error(f"Failed to load action cache: {e}")

    def _build_context(self, action_context: ckan_rpc_pb2.ActionContext) -> Dict[str, Any]:
        """
        Build a CKAN context dictionary from the gRPC request context.

        Args:
            action_context: The ActionContext protobuf message

        Returns:
            A dictionary suitable for CKAN action calls
        """
        context = {
            'user': action_context.user or None,
            'api_version': action_context.api_version or 3,
            'ignore_auth': False,
        }

        # Load user object if user is specified
        if action_context.user:
            try:
                user = User.get(action_context.user)
                if user:
                    context['auth_user_obj'] = user
            except Exception as e:
                log.warning(f"Failed to load user {action_context.user}: {e}")

        # Add any additional context extras
        if action_context.extras:
            context.update(action_context.extras)

        return context

    def _struct_to_dict(self, struct: struct_pb2.Struct) -> Dict[str, Any]:
        """Convert a protobuf Struct to a Python dictionary."""
        if not struct:
            return {}
        return json.loads(json_format.MessageToJson(struct))

    def _dict_to_struct(self, data: Dict[str, Any]) -> struct_pb2.Struct:
        """Convert a Python dictionary to a protobuf Struct."""
        return json_format.ParseDict(data, struct_pb2.Struct())

    def _build_error_response(
        self,
        error: Exception,
        action_name: str
    ) -> ckan_rpc_pb2.ActionError:
        """Build an ActionError from an exception."""
        error_msg = ckan_rpc_pb2.ActionError()
        error_msg.type = error.__class__.__name__
        error_msg.message = str(error)

        # Extract validation errors if available
        if isinstance(error, ValidationError):
            if hasattr(error, 'error_dict'):
                for field, errors in error.error_dict.items():
                    error_msg.field_errors[field].CopyFrom(
                        ckan_rpc_pb2.ActionError.FieldErrorsEntry(
                            key=field,
                            value=ckan_rpc_pb2.ActionError.FieldErrorsEntry.ValueEntry(
                                items=[e if isinstance(e, str) else str(e) for e in errors]
                            )
                        ).value
                    )
            elif hasattr(error, '__iter__'):
                error_msg.field_errors['__all__'].extend(
                    str(e) for e in error
                )

        return error_msg

    def ExecuteAction(
        self,
        request: ckan_rpc_pb2.ActionRequest,
        context: grpc.ServicerContext
    ) -> ckan_rpc_pb2.ActionResponse:
        """
        Execute a single RPC action.

        Args:
            request: The ActionRequest protobuf message
            context: gRPC context

        Returns:
            The ActionResponse protobuf message
        """
        response = ckan_rpc_pb2.ActionResponse()

        try:
            # Get the action function
            action_func = get_action(request.action)
            if not action_func:
                raise NotFound(f"Action '{request.action}' not found")

            # Build the CKAN context
            ckan_context = self._build_context(request.context)

            # Convert protobuf data to dictionary
            data_dict = self._struct_to_dict(request.data)

            # Execute the action
            log.debug(f"Executing action: {request.action}")
            result = action_func(ckan_context, data_dict)

            # Build successful response
            response.success = True
            response.result.CopyFrom(self._dict_to_struct(result if isinstance(result, dict) else {'result': result}))
            response.help = f"/api/action/{request.action}"

            # Track changed entities if available
            if isinstance(result, dict):
                if 'id' in result:
                    entity = response.changed_entities.add()
                    entity.entity_type = request.action.split('_')[0]
                    entity.entity_id = result['id']
                    entity.operation = 'create' if 'create' in request.action else 'update'

        except NotAuthorized as e:
            log.warning(f"Authorization failed for action {request.action}: {e}")
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details(str(e))
            response.success = False
            response.error.CopyFrom(self._build_error_response(e, request.action))

        except NotFound as e:
            log.warning(f"Resource not found for action {request.action}: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            response.success = False
            response.error.CopyFrom(self._build_error_response(e, request.action))

        except ValidationError as e:
            log.warning(f"Validation failed for action {request.action}: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Validation error: {str(e)}")
            response.success = False
            response.error.CopyFrom(self._build_error_response(e, request.action))

        except Exception as e:
            log.error(f"Unexpected error executing action {request.action}: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")
            response.success = False
            response.error.CopyFrom(self._build_error_response(e, request.action))

        return response

    def ExecuteBatch(
        self,
        request: ckan_rpc_pb2.BatchActionRequest,
        context: grpc.ServicerContext
    ) -> ckan_rpc_pb2.BatchActionResponse:
        """
        Execute multiple RPC actions in batch.

        Args:
            request: The BatchActionRequest protobuf message
            context: gRPC context

        Returns:
            The BatchActionResponse protobuf message
        """
        response = ckan_rpc_pb2.BatchActionResponse()
        failed_count = 0

        for i, action_request in enumerate(request.requests):
            # Execute each action
            action_response = self.ExecuteAction(action_request, context)
            response.responses.append(action_response)

            if not action_response.success:
                failed_count += 1
                if request.stop_on_error:
                    log.debug(f"Stopping batch execution on error at request {i}")
                    break

        response.failed_count = failed_count
        response.all_succeeded = failed_count == 0

        return response

    def ListActions(
        self,
        request: ckan_rpc_pb2.ActionListRequest,
        context: grpc.ServicerContext
    ) -> ckan_rpc_pb2.ActionListResponse:
        """
        Get information about available actions.

        Args:
            request: The ActionListRequest protobuf message
            context: gRPC context

        Returns:
            The ActionListResponse protobuf message
        """
        response = ckan_rpc_pb2.ActionListResponse()

        try:
            # Get all available actions
            from ckan.logic import get_action

            # Load all actions into our cache if not already done
            if not self._action_cache:
                self._load_action_cache()

            # Filter actions based on request criteria
            filtered_actions = []
            for action_name in sorted(self._action_cache.keys()):
                # Filter by category if specified
                if request.category:
                    if not action_name.startswith(request.category.rstrip('_') + '_'):
                        continue

                # Filter by search term if specified
                if request.search:
                    if request.search.lower() not in action_name.lower():
                        continue

                try:
                    action_func = get_action(action_name)
                    action_info = self._get_action_info(action_name, action_func)
                    response.actions.append(action_info)
                    filtered_actions.append(action_name)
                except Exception as e:
                    log.debug(f"Failed to get info for action {action_name}: {e}")

            response.total = len(filtered_actions)

        except Exception as e:
            log.error(f"Error listing actions: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")

        return response

    def _get_action_info(
        self,
        action_name: str,
        action_func: Any
    ) -> ckan_rpc_pb2.ActionInfo:
        """Get metadata about an action function."""
        info = ckan_rpc_pb2.ActionInfo()
        info.name = action_name
        info.side_effect_free = getattr(action_func, 'side_effect_free', False)
        info.description = action_func.__doc__ or f"Action: {action_name}"

        # Try to extract schema information if available
        if hasattr(action_func, '__wrapped__'):
            original = action_func.__wrapped__
            if hasattr(original, '__doc__'):
                info.description = original.__doc__ or info.description

        # Extract parameters from docstring if available
        if action_func.__doc__:
            docstring = action_func.__doc__
            lines = docstring.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(':param'):
                    # Extract parameter name
                    parts = line.split(':param')[1].split(':')
                    if parts:
                        param_name = parts[0].strip()
                        info.optional.append(param_name)

        return info

    def GetAction(
        self,
        request: ckan_rpc_pb2.GetActionRequest,
        context: grpc.ServicerContext
    ) -> ckan_rpc_pb2.ActionInfo:
        """
        Get detailed information about a specific action.

        Args:
            request: The GetActionRequest protobuf message
            context: gRPC context

        Returns:
            The ActionInfo protobuf message
        """
        try:
            action_func = get_action(request.action_name)
            return self._get_action_info(request.action_name, action_func)
        except NotFound:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Action '{request.action_name}' not found")
            return ckan_rpc_pb2.ActionInfo()
        except Exception as e:
            log.error(f"Error getting action info for {request.action_name}: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")
            return ckan_rpc_pb2.ActionInfo()

    def ExecuteStream(
        self,
        request_iterator: Iterator[ckan_rpc_pb2.ActionRequest],
        context: grpc.ServicerContext
    ) -> Iterator[ckan_rpc_pb2.ActionResponse]:
        """
        Stream multiple action requests and return responses.

        Args:
            request_iterator: Iterator of ActionRequest messages
            context: gRPC context

        Yields:
            ActionResponse messages
        """
        try:
            for request in request_iterator:
                try:
                    response = self.ExecuteAction(request, context)
                    yield response
                except Exception as e:
                    log.error(f"Error in stream for action {request.action}: {e}", exc_info=True)
                    # Return error response but continue streaming
                    error_response = ckan_rpc_pb2.ActionResponse()
                    error_response.success = False
                    error_response.error.CopyFrom(
                        self._build_error_response(e, request.action)
                    )
                    yield error_response

        except Exception as e:
            log.error(f"Error in ExecuteStream: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")
