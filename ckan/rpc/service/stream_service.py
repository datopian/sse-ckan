"""
CKAN Stream RPC Service Implementation

This module implements the CkanStreamService gRPC interface, providing
streaming access to CKAN data for real-time updates and monitoring.
"""

import logging
from typing import Iterator, Optional
from datetime import datetime
from google.protobuf import json_format, timestamp_pb2

from ckan.logic import get_action
from ckan.model import Package, Resource, Activity
from ckan.db import Session

from ..proto import ckan_rpc_pb2, ckan_rpc_pb2_grpc

log = logging.getLogger(__name__)


class CkanStreamServiceImpl(ckan_rpc_pb2_grpc.CkanStreamServiceServicer):
    """
    gRPC service implementation for CKAN streaming.

    This service provides streaming access to CKAN data including:
    - Real-time package/dataset changes
    - Resource updates
    - Activity stream
    """

    def StreamPackages(
        self,
        request: ckan_rpc_pb2.PackageStreamRequest,
        context
    ) -> Iterator[ckan_rpc_pb2.Package]:
        """
        Stream package changes.

        Args:
            request: The PackageStreamRequest protobuf message
            context: gRPC context

        Yields:
            Package messages
        """
        try:
            query = Session.query(Package)

            # Filter by organization if specified
            if request.organization_id:
                query = query.filter(Package.owner_org == request.organization_id)

            # Filter by modification date if specified
            if request.since:
                since_dt = datetime.fromtimestamp(request.since.seconds)
                query = query.filter(Package.metadata_modified >= since_dt)

            # Filter by state if needed
            if not request.only_changed:
                query = query.filter(Package.state == 'active')

            # Order by modification date
            query = query.order_by(Package.metadata_modified)

            # Stream packages
            for package in query:
                try:
                    pkg_dict = self._package_to_proto(package)
                    yield pkg_dict
                except Exception as e:
                    log.error(f"Error converting package {package.id}: {e}")
                    continue

        except Exception as e:
            log.error(f"Error in StreamPackages: {e}", exc_info=True)
            context.set_code(context.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")

    def StreamResources(
        self,
        request: ckan_rpc_pb2.ResourceStreamRequest,
        context
    ) -> Iterator[ckan_rpc_pb2.Resource]:
        """
        Stream resource changes.

        Args:
            request: The ResourceStreamRequest protobuf message
            context: gRPC context

        Yields:
            Resource messages
        """
        try:
            query = Session.query(Resource)

            # Filter by package if specified
            if request.package_id:
                query = query.filter(Resource.package_id == request.package_id)

            # Filter by modification date if specified
            if request.since:
                since_dt = datetime.fromtimestamp(request.since.seconds)
                query = query.filter(Resource.last_modified >= since_dt)

            # Order by modification date
            query = query.order_by(Resource.last_modified)

            # Stream resources
            for resource in query:
                try:
                    res_dict = self._resource_to_proto(resource)
                    yield res_dict
                except Exception as e:
                    log.error(f"Error converting resource {resource.id}: {e}")
                    continue

        except Exception as e:
            log.error(f"Error in StreamResources: {e}", exc_info=True)
            context.set_code(context.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")

    def StreamActivity(
        self,
        request: ckan_rpc_pb2.ActivityStreamRequest,
        context
    ) -> Iterator[ckan_rpc_pb2.ActivityEntry]:
        """
        Stream activity/change log entries.

        Args:
            request: The ActivityStreamRequest protobuf message
            context: gRPC context

        Yields:
            ActivityEntry messages
        """
        try:
            query = Session.query(Activity)

            # Filter by user if specified
            if request.user_id:
                query = query.filter(Activity.user_id == request.user_id)

            # Filter by object type if specified
            if request.object_type:
                query = query.filter(Activity.object_id == request.object_type)

            # Filter by timestamp if specified
            if request.since:
                since_dt = datetime.fromtimestamp(request.since.seconds)
                query = query.filter(Activity.timestamp >= since_dt)

            # Order by timestamp descending (most recent first)
            query = query.order_by(Activity.timestamp.desc())

            # Stream activity entries
            for activity in query:
                try:
                    activity_entry = self._activity_to_proto(activity)
                    yield activity_entry
                except Exception as e:
                    log.error(f"Error converting activity {activity.id}: {e}")
                    continue

        except Exception as e:
            log.error(f"Error in StreamActivity: {e}", exc_info=True)
            context.set_code(context.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")

    def _package_to_proto(self, package: Package) -> ckan_rpc_pb2.Package:
        """Convert a CKAN Package model to protobuf Package message."""
        pkg = ckan_rpc_pb2.Package()

        pkg.id = package.id or ""
        pkg.name = package.name or ""
        pkg.title = package.title or ""
        pkg.notes = package.notes or ""
        pkg.state = package.state or "active"

        if package.metadata_created:
            pkg.created.FromDatetime(package.metadata_created)

        if package.metadata_modified:
            pkg.last_modified.FromDatetime(package.metadata_modified)

        # Add resources
        for resource in package.resources:
            res = self._resource_to_proto(resource)
            pkg.resources.append(res)

        # Add groups
        for group in package.groups:
            grp = ckan_rpc_pb2.Group()
            grp.id = group.id or ""
            grp.name = group.name or ""
            grp.title = group.title or ""
            pkg.groups.append(grp)

        return pkg

    def _resource_to_proto(self, resource: Resource) -> ckan_rpc_pb2.Resource:
        """Convert a CKAN Resource model to protobuf Resource message."""
        res = ckan_rpc_pb2.Resource()

        res.id = resource.id or ""
        res.package_id = resource.package_id or ""
        res.url = resource.url or ""
        res.format = resource.format or ""
        res.description = resource.description or ""
        res.name = resource.name or ""
        res.hash = resource.hash or ""
        res.size = resource.size or 0

        if resource.created:
            res.created.FromDatetime(resource.created)

        if resource.last_modified:
            res.last_modified.FromDatetime(resource.last_modified)

        return res

    def _activity_to_proto(self, activity: Activity) -> ckan_rpc_pb2.ActivityEntry:
        """Convert a CKAN Activity model to protobuf ActivityEntry message."""
        entry = ckan_rpc_pb2.ActivityEntry()

        entry.id = activity.id or ""
        entry.user_id = activity.user_id or ""
        entry.object_id = activity.object_id or ""
        entry.object_type = activity.activity_type or ""
        entry.activity_type = activity.activity_type or ""

        if activity.timestamp:
            entry.timestamp = activity.timestamp.isoformat()

        # Add data if available
        if hasattr(activity, 'data') and activity.data:
            try:
                import json
                data_dict = json.loads(activity.data) if isinstance(activity.data, str) else activity.data
                from google.protobuf import json_format
                entry.data.CopyFrom(
                    json_format.ParseDict(data_dict, entry.data.__class__())
                )
            except Exception as e:
                log.debug(f"Could not parse activity data: {e}")

        return entry
