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
        valid_bundle_types = {"transaction", "collection"}
        if bundle_type not in valid_bundle_types:
            raise ValueError(f"Unsupported bundle type: {bundle_type}")

        valid_methods = {"POST", "PUT", "CONDITIONAL"}
        if bundle_type == "transaction" and request_method not in valid_methods:
            raise ValueError(f"Unsupported request method: {request_method}")

        bundle_id = str(uuid.uuid4())
        entries: List[BundleEntry] = []

        for resource in resources:
            entry = self._create_bundle_entry(resource, bundle_type, request_method, urn_mapping)
            entries.append(entry)

        bundle = Bundle(
            id=bundle_id,
            type=bundle_type,
            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            entry=entries,
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
        resource_type = resource.resource_type

        if request_method == "POST":
            if urn_mapping and resource.id in urn_mapping:
                urn_uuid = urn_mapping[resource.id]
            else:
                urn_uuid = str(uuid.uuid4())

            resource_dict = resource.model_dump(by_alias=True, exclude_none=True)
            resource_dict.pop("id", None)

            if urn_mapping:
                self._update_references(resource_dict, urn_mapping)

            resource_class = resource.__class__
            resource_without_id = resource_class(**resource_dict)

            entry = BundleEntry(
                resource=resource_without_id,
                fullUrl=f"urn:uuid:{urn_uuid}",
            )
        else:
            entry = BundleEntry(
                resource=resource,
                fullUrl=f"urn:uuid:{resource.id}",
            )

        # Add request for transaction bundles
        if bundle_type == "transaction":
            if request_method == "PUT":
                # PUT with conditional update (upsert)
                # ifNoneMatch: * means create if doesn't exist
                entry.request = BundleEntryRequest(
                    method="PUT",
                    url=f"{resource_type}/{resource.id}",
                    ifNoneMatch="*"
                )
            elif request_method == "CONDITIONAL":
                identifier_value = None
                if hasattr(resource, "identifier") and resource.identifier:
                    ident = resource.identifier[0]
                    ident_system = getattr(ident, "system", None)
                    ident_value = getattr(ident, "value", None)
                    if ident_system and ident_value:
                        identifier_value = f"{ident_system}|{ident_value}"
                    elif ident_value:
                        identifier_value = ident_value

                if not identifier_value:
                    identifier_value = resource.id

                entry.request = BundleEntryRequest(
                    method="POST",
                    url=f"{resource_type}?identifier={identifier_value}",
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

    def _update_references(self, data: Any, urn_mapping: Dict[str, str]) -> None:
        """Update resource references to URN values for POST bundles."""

        if isinstance(data, dict):
            for key, value in data.items():
                if key == "reference" and isinstance(value, str):
                    if value.startswith("urn:uuid:"):
                        continue
                    parts = value.split("/")
                    if len(parts) == 2:
                        ref_id = parts[1]
                        if ref_id in urn_mapping:
                            data[key] = f"urn:uuid:{urn_mapping[ref_id]}"
                else:
                    self._update_references(value, urn_mapping)
        elif isinstance(data, list):
            for item in data:
                self._update_references(item, urn_mapping)
