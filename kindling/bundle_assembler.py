"""Bundle assembler for creating FHIR bundles."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.resource import Resource


class BundleAssembler:
    """Assembler for creating FHIR bundles."""

    def create_bundle(
        self,
        resources: List[Resource],
        bundle_type: str = "transaction",
        request_method: str = "POST",
        urn_mapping: Optional[Dict[str, str]] = None
    ) -> Bundle:
        """Create a single FHIR bundle from resources.

        Args:
            resources: List of FHIR resources
            bundle_type: Type of bundle ("transaction" or "collection")
            request_method: HTTP method for transaction bundles ("POST" or "PUT")
            urn_mapping: Mapping from resource IDs to URN UUIDs

        Returns:
            FHIR Bundle
        """
        bundle_id = str(uuid.uuid4())
        entries = []

        for resource in resources:
            entry = self._create_bundle_entry(resource, bundle_type, request_method, urn_mapping)
            entries.append(entry)

        bundle = Bundle(
            id=bundle_id,
            type=bundle_type,
            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            entry=entries if entries else None
        )

        return bundle

    def create_bundles(
        self,
        resources: List[Resource],
        bundle_type: str = "transaction",
        bundle_size: int = 100,
        request_method: str = "POST",
        urn_mapping: Optional[Dict[str, str]] = None
    ) -> List[Bundle]:
        """Create multiple FHIR bundles from resources.

        Args:
            resources: List of FHIR resources
            bundle_type: Type of bundle ("transaction" or "collection")
            bundle_size: Maximum resources per bundle
            request_method: HTTP method for transaction bundles ("POST" or "PUT")
            urn_mapping: Mapping from resource IDs to URN UUIDs

        Returns:
            List of FHIR Bundles
        """
        bundles = []

        # Split resources into chunks
        for i in range(0, len(resources), bundle_size):
            chunk = resources[i:i + bundle_size]
            bundle = self.create_bundle(chunk, bundle_type, request_method, urn_mapping)
            bundles.append(bundle)

        # Ensure at least one empty bundle if no resources
        if not bundles:
            bundles.append(self.create_bundle([], bundle_type, request_method, urn_mapping))

        return bundles

    def _create_bundle_entry(
        self,
        resource: Resource,
        bundle_type: str,
        request_method: str = "POST",
        urn_mapping: Optional[Dict[str, str]] = None
    ) -> BundleEntry:
        """Create a bundle entry for a resource.

        Args:
            resource: FHIR resource
            bundle_type: Type of bundle
            request_method: HTTP method for transaction bundles ("POST" or "PUT")
            urn_mapping: Mapping from resource IDs to URN UUIDs

        Returns:
            BundleEntry
        """
        # For POST method, use URN UUID and remove resource.id
        if request_method == "POST":
            if urn_mapping and resource.id in urn_mapping:
                # Get the URN UUID for this resource
                urn_uuid = urn_mapping[resource.id]
            else:
                # Generate a new URN UUID if not in mapping
                urn_uuid = str(uuid.uuid4())

            # Create a copy of the resource without the id field
            resource_dict = resource.dict()
            # Remove the id field
            resource_dict.pop('id', None)
            resource_class = resource.__class__
            resource_without_id = resource_class(**resource_dict)

            entry = BundleEntry(
                resource=resource_without_id,
                fullUrl=f"urn:uuid:{urn_uuid}"
            )
        else:
            # For PUT or other methods, keep the resource ID
            entry = BundleEntry(
                resource=resource,
                fullUrl=f"urn:uuid:{resource.id}"
            )

        # Add request for transaction bundles
        if bundle_type == "transaction":
            resource_type = resource.__class__.__name__
            if request_method == "PUT":
                # PUT with conditional update (upsert)
                # ifNoneMatch: * means create if doesn't exist
                entry.request = BundleEntryRequest(
                    method="PUT",
                    url=f"{resource_type}/{resource.id}",
                    ifNoneMatch="*"
                )
            elif request_method == "CONDITIONAL":
                # Conditional create using identifier
                # This creates if no matching identifier exists
                identifier_value = None
                if hasattr(resource, 'identifier') and resource.identifier:
                    # Use first identifier as condition
                    ident = resource.identifier[0]
                    identifier_value = f"{ident.system}|{ident.value}"

                if identifier_value and resource_type == "Patient":
                    entry.request = BundleEntryRequest(
                        method="POST",
                        url=resource_type,
                        ifNoneExist=f"identifier={identifier_value}"
                    )
                else:
                    # Regular POST for resources without identifiers
                    entry.request = BundleEntryRequest(
                        method="POST",
                        url=resource_type
                    )
            else:
                # POST creates new resource, server assigns ID
                # Add ifNoneExist for Patient resources with identifiers
                if resource_type == "Patient" and hasattr(resource, 'identifier') and resource.identifier:
                    # Use first identifier as condition
                    ident = resource.identifier[0]
                    identifier_value = f"{ident.system}|{ident.value}"
                    entry.request = BundleEntryRequest(
                        method="POST",
                        url=resource_type,
                        ifNoneExist=f"identifier={identifier_value}"
                    )
                else:
                    entry.request = BundleEntryRequest(
                        method="POST",
                        url=resource_type
                    )

        return entry