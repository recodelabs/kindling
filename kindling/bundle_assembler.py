"""Bundle assembler for creating FHIR bundles."""

import uuid
from datetime import datetime
from typing import Any, List

from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.resource import Resource


class BundleAssembler:
    """Assembler for creating FHIR bundles."""

    def create_bundle(
        self,
        resources: List[Resource],
        bundle_type: str = "transaction"
    ) -> Bundle:
        """Create a single FHIR bundle from resources.

        Args:
            resources: List of FHIR resources
            bundle_type: Type of bundle ("transaction" or "collection")

        Returns:
            FHIR Bundle
        """
        bundle_id = str(uuid.uuid4())
        entries = []

        for resource in resources:
            entry = self._create_bundle_entry(resource, bundle_type)
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
        bundle_size: int = 100
    ) -> List[Bundle]:
        """Create multiple FHIR bundles from resources.

        Args:
            resources: List of FHIR resources
            bundle_type: Type of bundle ("transaction" or "collection")
            bundle_size: Maximum resources per bundle

        Returns:
            List of FHIR Bundles
        """
        bundles = []

        # Split resources into chunks
        for i in range(0, len(resources), bundle_size):
            chunk = resources[i:i + bundle_size]
            bundle = self.create_bundle(chunk, bundle_type)
            bundles.append(bundle)

        # Ensure at least one empty bundle if no resources
        if not bundles:
            bundles.append(self.create_bundle([], bundle_type))

        return bundles

    def _create_bundle_entry(
        self,
        resource: Resource,
        bundle_type: str
    ) -> BundleEntry:
        """Create a bundle entry for a resource.

        Args:
            resource: FHIR resource
            bundle_type: Type of bundle

        Returns:
            BundleEntry
        """
        entry = BundleEntry(
            resource=resource,
            fullUrl=f"urn:uuid:{resource.id}"
        )

        # Add request for transaction bundles
        if bundle_type == "transaction":
            resource_type = resource.__class__.__name__
            entry.request = BundleEntryRequest(
                method="POST",
                url=resource_type
            )

        return entry