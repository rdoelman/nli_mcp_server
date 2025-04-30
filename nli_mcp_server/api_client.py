"""
API client for interacting with the National Library of Israel APIs.
"""

import urllib.parse
from typing import Any, Dict, List, Tuple

import httpx

from nli_mcp_server.api_models import (
    Format,
    ImageInfo,
    Quality,
    Region,
    Rotation,
    SearchParams,
    Size,
)


class ApiClientError(Exception):
    """Base exception for API client errors."""

    pass


class SearchApiClient:
    """Client for interacting with the NLI Search API."""

    BASE_URL = "https://merhav.nli.org.il/PrimoWebServices/xservice/search/brief"

    async def search(self, params: SearchParams) -> Dict[str, Any]:
        """
        Perform a search using the NLI Search API.
        Args:
            params: Search parameters
        Returns:
            Search results as a dictionary
        Raises:
            ApiClientError: If the API request fails
        """
        # Base parts of the URL
        base_url = self.BASE_URL
        query_parts = [
            f"institution={params.institution}",
            f"loc=local,scope:({params.scope_name})",
            f"indx={params.start_index}",
            f"bulkSize={params.page_size}",
            f"json={'true' if params.json_format else 'false'}",
        ]

        # Add search queries
        for query in params.queries:
            query_string = query.to_query_param()
            query_parts.append(f"query={urllib.parse.quote(query_string)}")

        # Add resource type filters
        if params.rtype:
            resource_values = ",".join(
                [resource_type.value for resource_type in params.rtype]
            )
            rtype_query = f"facet_rtype,exact,{resource_values}"
            query_parts.append(f"query_inc={urllib.parse.quote(rtype_query)}")

        # Construct the full URL with all parameters
        url = f"{base_url}?{'&'.join(query_parts)}"

        # print(f"Request URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                # Make the request with the manually constructed URL
                # We're passing an empty params dict since we included all params in the URL
                response = await client.get(url)
                response.raise_for_status()
                if params.json_format:
                    return response.json()
                else:
                    return {"xml_content": response.text}
            except httpx.HTTPStatusError as e:
                raise ApiClientError(f"HTTP error: {e}")
            except httpx.RequestError as e:
                raise ApiClientError(f"Request error: {e}")
            except Exception as e:
                raise ApiClientError(f"Unexpected error: {e}")

    async def extract_record_ids(self, search_results: Dict[str, Any]) -> List[str]:
        """
        Extract record IDs from search results.

        Args:
            search_results: Search results from the search method

        Returns:
            List of record IDs
        """
        record_ids = []

        try:
            # Navigate the JSON structure to find record IDs
            segments = search_results.get("SEGMENTS", {})
            jagroot = segments.get("JAGROOT", {})
            result = jagroot.get("RESULT", {})
            docset = result.get("DOCSET", {})
            docs = docset.get("DOC", [])

            for doc in docs:
                primo_bib = doc.get("PrimoNMBib", {})
                record = primo_bib.get("record", {})
                control = record.get("control", {})
                record_id = control.get("recordid")

                if record_id:
                    record_ids.append(record_id)
        except Exception as e:
            # Just log and continue - this is not a critical error
            print(f"Error extracting record IDs: {e}")

        return record_ids


class IiifApiClient:
    """Client for interacting with the IIIF APIs."""

    IMAGE_API_BASE_URL = "http://iiif.nli.org.il/IIIFv21"

    async def get_image_info(self, identifier: str) -> ImageInfo:
        """
        Get information about an image using the IIIF Image Information API.

        Args:
            identifier: Image identifier

        Returns:
            Information about the image

        Raises:
            ApiClientError: If the API request fails
        """
        url = f"{self.IMAGE_API_BASE_URL}/{identifier}/info.json"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return ImageInfo.from_json(identifier, data)
            except httpx.HTTPStatusError as e:
                raise ApiClientError(f"HTTP error: {e}")
            except httpx.RequestError as e:
                raise ApiClientError(f"Request error: {e}")
            except Exception as e:
                raise ApiClientError(f"Unexpected error: {e}")

    def build_image_url(
        self,
        identifier: str,
        region: str,
        size: str,
        rotation: str,
        quality: Quality = Quality.DEFAULT,
        image_format: Format = Format.JPG,
    ) -> str:
        """
        Build a URL for the IIIF Image API.

        Args:
            identifier: Image identifier
            region: Region parameter (use Region class helper methods)
            size: Size parameter (use Size class helper methods)
            rotation: Rotation parameter (use Rotation class helper methods)
            quality: Image quality
            image_format: Image format

        Returns:
            IIIF Image API URL
        """
        return f"{self.IMAGE_API_BASE_URL}/{identifier}/{region}/{size}/{rotation}/{quality.value}.{image_format.value}"

    async def get_image_data(
        self,
        identifier: str,
        region: str = "full",
        size: str = "max",
        rotation: str = "0",
        quality: Quality = Quality.DEFAULT,
        image_format: Format = Format.JPG,
    ) -> bytes:
        """
        Get image data using the IIIF Image API.

        Args:
            identifier: Image identifier
            region: Region parameter
            size: Size parameter
            rotation: Rotation parameter
            quality: Image quality
            image_format: Image format

        Returns:
            Image data as bytes

        Raises:
            ApiClientError: If the API request fails
        """
        url = self.build_image_url(
            identifier,
            region,
            size,
            rotation,
            quality,
            image_format,
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
            except httpx.HTTPStatusError as e:
                raise ApiClientError(f"HTTP error: {e}")
            except httpx.RequestError as e:
                raise ApiClientError(f"Request error: {e}")
            except Exception as e:
                raise ApiClientError(f"Unexpected error: {e}")

    def generate_tiles(
        self, image_info: ImageInfo, tile_size: int = 256
    ) -> List[Tuple[str, str, str, str]]:
        """
        Generate tile parameters for retrieving a large image as tiles.

        Args:
            image_info: Information about the image
            tile_size: Size of each tile in pixels

        Returns:
            List of (region, size, rotation, url) tuples for each tile
        """
        tiles = []

        # Calculate number of tiles in x and y directions
        num_x_tiles = (image_info.width + tile_size - 1) // tile_size
        num_y_tiles = (image_info.height + tile_size - 1) // tile_size

        for y in range(num_y_tiles):
            for x in range(num_x_tiles):
                # Calculate pixel coordinates
                pixel_x = x * tile_size
                pixel_y = y * tile_size
                pixel_width = min(tile_size, image_info.width - pixel_x)
                pixel_height = min(tile_size, image_info.height - pixel_y)

                # Calculate percentage coordinates
                pct_x = (pixel_x / image_info.width) * 100
                pct_y = (pixel_y / image_info.height) * 100
                pct_width = (pixel_width / image_info.width) * 100
                pct_height = (pixel_height / image_info.height) * 100

                # Create region parameter
                region = Region.percentage(pct_x, pct_y, pct_width, pct_height)

                # Create size parameter
                size = Size.width(tile_size)

                # Create rotation parameter
                rotation = Rotation.none()

                # Create URL
                url = self.build_image_url(
                    image_info.identifier, region, size, rotation
                )

                tiles.append((region, size, rotation, url))

        return tiles
