# CKAN Extensions and gRPC RPC Service

## Automatic Extension Integration

Yes! **All CKAN extensions that implement the `IActions` interface will automatically have their actions available via gRPC RPC**, without any additional configuration or code changes needed.

## How It Works

### The Action Dispatcher

The RPC service uses CKAN's core `get_action()` function to retrieve action handlers:

```python
# In action_service.py
action_func = get_action(request.action)
```

The `get_action()` function is CKAN's unified action dispatcher that:

1. **Loads core actions** from built-in modules:
   - `ckan/logic/action/get.py` - Read operations
   - `ckan/logic/action/create.py` - Create operations
   - `ckan/logic/action/update.py` - Update operations
   - `ckan/logic/action/delete.py` - Delete operations
   - `ckan/logic/action/patch.py` - Partial updates

2. **Loads plugin actions** by iterating through all plugins implementing `IActions`:
   ```python
   for plugin in p.PluginImplementations(p.IActions):
       for name, action_function in plugin.get_actions().items():
           # Register plugin actions
   ```

3. **Handles action overrides** - Plugins can replace core actions
4. **Handles action chaining** - Plugins can wrap existing actions
5. **Caches actions** for performance

Since RPC uses the same `get_action()`, **it automatically gets all extension actions**.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    RPC Request                          │
│         ExecuteAction(action_name, data)                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │    get_action(action_name)   │
        │   (Core dispatcher)          │
        └──────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Core    │  │ Plugin 1 │  │ Plugin 2 │
    │ Actions  │  │ Actions  │  │ Actions  │
    └──────────┘  └──────────┘  └──────────┘
          │            │            │
          └────────────┴────────────┘
                       │
                       ▼
            ┌───────────────────────┐
            │  Matched Action Func  │
            └───────────────────────┘
                       │
                       ▼
            ┌───────────────────────┐
            │  Execute with CKAN    │
            │  Context & DB Access  │
            └───────────────────────┘
```

## Extension Examples

### Example 1: Custom Action via IActions

Create a plugin with custom action:

```python
# ckanext-myext/ckanext/myext/logic/action.py

import ckan.plugins.toolkit as toolkit

def my_custom_action(context, data_dict):
    """Custom action available via REST API and RPC."""
    # Validate authorization
    toolkit.check_access('my_custom_action', context)

    # Execute custom logic
    result = {
        'message': 'Hello from custom action!',
        'input': data_dict
    }
    return result

# Plugin interface
# ckanext-myext/ckanext/myext/plugin.py

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

class MyExtPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {
            'my_custom_action': my_custom_action,
        }
```

Now call it via RPC:

```python
import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc
from google.protobuf import json_format, struct_pb2

async def call_custom_action():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = ckan_rpc_pb2_grpc.CkanActionServiceStub(channel)

        request = ckan_rpc_pb2.ActionRequest()
        request.action = 'my_custom_action'  # Automatically available!
        request.context.user = 'admin'
        request.data.CopyFrom(json_format.ParseDict(
            {'key': 'value'},
            struct_pb2.Struct()
        ))

        response = await stub.ExecuteAction(request)
        if response.success:
            result = json_format.MessageToDict(response.result)
            print(f"Result: {result}")
        else:
            print(f"Error: {response.error.message}")

asyncio.run(call_custom_action())
```

### Example 2: Override Core Action

Plugin that enhances the package_create action:

```python
# ckanext-enhanced/ckanext/enhanced/logic/action.py

import ckan.plugins.toolkit as toolkit
from ckan.logic.action.create import package_create as core_package_create

def enhanced_package_create(context, data_dict):
    """Enhanced package_create that adds extra validation."""

    # Custom pre-processing
    if 'custom_field' not in data_dict:
        data_dict['custom_field'] = 'default_value'

    # Call original action
    result = core_package_create(context, data_dict)

    # Custom post-processing
    result['creation_method'] = 'rpc'

    return result

# Plugin interface
import ckan.plugins as plugins

class EnhancedPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {
            'package_create': enhanced_package_create,  # Override!
        }
```

Now the enhanced version is used for both REST and RPC:

```python
# This now uses the enhanced version
request = ckan_rpc_pb2.ActionRequest()
request.action = 'package_create'
response = await stub.ExecuteAction(request)
```

### Example 3: Chained Action

Plugin that wraps an existing action:

```python
# ckanext-logging/ckanext/logging/logic/action.py

import ckan.plugins.toolkit as toolkit
import logging

log = logging.getLogger(__name__)

@toolkit.chained_action
def package_create(original_action, context, data_dict):
    """Wrap package_create with logging."""

    # Pre-processing
    log.info(f"Creating package: {data_dict.get('name')}")

    # Call original action
    result = original_action(context, data_dict)

    # Post-processing
    log.info(f"Created package: {result['id']}")

    return result

# Plugin
import ckan.plugins as plugins

class LoggingPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {
            'package_create': package_create,  # Chain!
        }
```

## How Extension Actions Appear in RPC

### Discovery via ListActions

Extensions are automatically discovered by the RPC service:

```python
# List all actions (including extension actions)
request = ckan_rpc_pb2.ActionListRequest()
response = await stub.ListActions(request)

# Results include:
# - Core CKAN actions
# - All extension actions
# - Any overridden/chained actions
for action in response.actions:
    print(f"Action: {action.name}")
    print(f"  Description: {action.description}")
    print(f"  Side-effect free: {action.side_effect_free}")
```

### Searching Extensions

Filter extension actions:

```python
# Find all custom actions (pattern-based)
request = ckan_rpc_pb2.ActionListRequest()
request.search = 'custom'
response = await stub.ListActions(request)

# Find all extension actions starting with 'my_'
request = ckan_rpc_pb2.ActionListRequest()
request.search = 'my_'
response = await stub.ListActions(request)
```

## Testing Extension Actions

### Unit Tests

Test your extension's RPC availability:

```python
# ckanext-myext/ckanext/myext/tests/test_rpc.py

import pytest
import asyncio
import grpc
from ckan.rpc.proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc
from google.protobuf import json_format, struct_pb2
import ckan.tests.factories as factories

@pytest.mark.usefixtures('clean_db', 'with_request_context')
class TestMyExtRPC:
    """Test custom action via RPC."""

    def test_my_custom_action_via_rpc(self):
        """Test that custom action works via RPC."""
        # This is a simplified example - would need async handling
        from ckan.rpc.service.action_service import CkanActionServiceImpl

        service = CkanActionServiceImpl()
        mock_context = type('obj', (object,), {
            'set_code': lambda x: None,
            'set_details': lambda x: None
        })()

        request = ckan_rpc_pb2.ActionRequest()
        request.action = 'my_custom_action'
        request.context.user = 'admin'

        response = service.ExecuteAction(request, mock_context)

        assert response.success is True
        result = json_format.MessageToDict(response.result)
        assert 'message' in result
```

### Integration Tests

Test with real RPC server:

```bash
# In Docker, run tests
docker-compose -f docker-compose-rpc.yml exec ckan \
  pytest ckanext/myext/tests/test_rpc.py -v
```

## Extension Compatibility

### Required for RPC Support

✅ **Already supported - no changes needed:**
- Any extension using standard `IActions` interface
- Custom actions with standard CKAN patterns
- Authorization checks
- Validation schemas
- Context and database access

### Automatic Translation

RPC automatically handles:
- ✅ Python dict ↔ Protobuf Struct conversion
- ✅ Authorization checks (uses CKAN's auth system)
- ✅ Validation (uses CKAN's schema system)
- ✅ Error handling (converts to gRPC errors)
- ✅ Database transactions (CKAN's session management)
- ✅ File uploads (if passed as binary data)

### Best Practices for Extensions

When designing extensions for RPC compatibility:

1. **Use standard patterns**:
   ```python
   def my_action(context, data_dict):
       # Standard CKAN action signature
       toolkit.check_access('my_action', context)
       # ... validation
       # ... logic
       return result  # Returns dict
   ```

2. **Validate input**:
   ```python
   from ckan.logic import validate

   @validate(schema.my_schema)
   def my_action(context, data_dict):
       # data_dict is already validated
       pass
   ```

3. **Use toolkit.get_action** for dependencies:
   ```python
   def my_action(context, data_dict):
       # Good - works via RPC too
       pkg = toolkit.get_action('package_show')(context, {'id': pkg_id})

       # Avoid direct imports when possible
       # NOT: from ckan.logic.action.get import package_show
   ```

4. **Document your actions**:
   ```python
   def my_action(context, data_dict):
       """
       My custom action description.

       :param name: Package name
       :type name: string
       :returns: Package information
       :rtype: dict
       """
   ```

## Limitations and Edge Cases

### What Works

✅ All standard CKAN action patterns
✅ Custom actions
✅ Overridden actions
✅ Chained actions
✅ Authorization
✅ Validation
✅ Database operations
✅ Batch operations
✅ Streaming

### Edge Cases

⚠️ **File uploads**: Work but passed as binary in Protobuf Struct
⚠️ **Large responses**: May hit message size limits (configurable)
⚠️ **Streaming data**: Use StreamService for large datasets
⚠️ **Side effects**: RPC executes the same logic - same side effects occur

## Extension Development Workflow

### 1. Develop Extension Normally

```bash
# Create extension with IActions
ckan generate extension myext
cd ckanext-myext
```

### 2. Test with REST API

```bash
# Test traditional REST API
curl -X POST http://localhost:5000/api/3/action/my_custom_action \
  -H "Authorization: <token>" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

### 3. Automatically Test with RPC

```python
# Same action works via RPC without any changes!
request = ckan_rpc_pb2.ActionRequest()
request.action = 'my_custom_action'
response = await stub.ExecuteAction(request)
```

### 4. Document Both Interfaces

The action documentation is automatically available:

```python
# In your action docstring
def my_custom_action(context, data_dict):
    """
    My custom action.

    Available via:
    - REST API: POST /api/3/action/my_custom_action
    - gRPC RPC: CkanActionService.ExecuteAction('my_custom_action')

    Parameters:
      key (string): Some key

    Returns:
      dict with result
    """
```

## Discovery and Introspection

### List Extension Actions

```python
# Get all actions
all_actions = await stub.ListActions(ckan_rpc_pb2.ActionListRequest())

# Get extension actions (heuristic - starts with extension name)
ext_actions = await stub.ListActions(
    ckan_rpc_pb2.ActionListRequest(search='myext')
)

# Get action details
info = await stub.GetAction(
    ckan_rpc_pb2.GetActionRequest(action_name='my_custom_action')
)
```

## Conclusion

The RPC service is **completely transparent** to CKAN extensions. Any extension that:
1. Implements the standard `IActions` interface
2. Follows CKAN action patterns
3. Works with the REST API

...will **automatically work with gRPC RPC** without any modifications needed!

This provides users with maximum flexibility:
- Existing extensions continue to work
- Extensions gain RPC access automatically
- No changes to extension code required
- Both REST and RPC APIs share the same action logic
