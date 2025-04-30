"""
Core MCP server implementation for the National Library of Israel API interface.
"""

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP, Image

from nli_mcp_server.api_client import (
    ApiClientError,
    IiifApiClient,
    SearchApiClient,
)
from nli_mcp_server.api_models import (
    AvailabilityType,
    FacetField,
    Format,
    PrecisionOperator,
    Quality,
    ResourceType,
    SearchField,
    SearchParams,
)


def extract_image_info(record_data):
    """
    Extract image URLs, IDs, and resource information from API results.
    Searches all fields for URLs without making assumptions about ID formats.

    Args:
        record_data (dict): The record dictionary from the API response

    Returns:
        dict: A dictionary containing:
            - urls (list): All found URLs
            - document_ids (list): All extracted document IDs from URLs
            - is_online (bool): Whether the resource is available online
    """
    result = {"urls": [], "document_ids": [], "is_online": False}

    # Early return if record_data is None or not a dictionary
    if not record_data or not isinstance(record_data, dict):
        return result

    # Check if it's an online resource
    if "facets" in record_data and "toplevel" in record_data["facets"]:
        result["is_online"] = record_data["facets"]["toplevel"] == "online_resources"
    elif "delivery" in record_data and "delcategory" in record_data["delivery"]:
        result["is_online"] = (
            record_data["delivery"]["delcategory"] == "Online Resource"
        )

    # Function to recursively search for URLs in any field
    def find_urls_in_dict(data):
        if isinstance(data, dict):
            find_urls_in_dict(list(data.values()))
        elif isinstance(data, list):
            for item in data:
                find_urls_in_dict(item)
        elif isinstance(data, str):
            # Look for URLs
            if data.startswith("https"):
                # Clean up URL if it has trailing punctuation
                url = data.rstrip(",.;:")
                if url not in result["urls"]:
                    result["urls"].append(url)
                    # Try to extract ID if present in URL
                    if "dps_pid=" in url:
                        if "stream" in url:
                            pid = (
                                url.split("dps_pid=")[1].split("&")[0]
                                if "&" in url
                                else url.split("dps_pid=")[1]
                            )
                            if pid and pid not in result["document_ids"]:
                                result["document_ids"].append(pid)

    # Start recursive search on the entire record
    find_urls_in_dict(record_data)

    # Filter out terms of use URLs if any slipped through
    result["urls"] = [
        url for url in result["urls"] if "terms-of-use" not in url.lower()
    ]

    return result


class NliMcpServer:
    """
    MCP server for the National Library of Israel APIs.

    This server provides tools for:
    - Searching for items in the NLI catalog
    - Retrieving images via the IIIF Image API
    - Getting information about images
    """

    def __init__(self, server_name: str = "nli_mcp"):
        """
        Initialize the NLI MCP server.

        Args:
            server_name: Name of the MCP server
        """
        self.name = "nli_mcp"
        self.mcp = FastMCP(server_name)
        self.search_client = SearchApiClient()
        self.iiif_client = IiifApiClient()
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all tools with the MCP server."""
        # Register search-related tools
        self.mcp.tool()(self.search_catalog)

        # Register IIIF-related tools
        self.mcp.tool()(self.get_image_info)
        self.mcp.tool()(self.get_image)
        self.mcp.tool()(self.get_tiled_image_urls)

    def run(self, transport: str = "stdio") -> None:
        """
        Run the MCP server.

        Args:
            transport: Transport mechanism to use ('stdio' or 'websocket')
        """
        self.mcp.run(transport=transport)

    # Search-related tools
    async def search_catalog(
        self,
        query: str,
        resource_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        creator: Optional[str] = None,
        availability: Optional[str] = None,
        institution: str = "NNL",
        scope: str = "NNL",
        start_index: int = 1,
        page_size: int = 10,
    ) -> str:
        """
        Search the NLI catalog with advanced filtering options.

        Args:
            query: The main search query
            resource_type: Type of resource to search for (e.g., "photograph", "book", ""periodical", "manuscript", "map", "ethnographic-recording", "radio-recording", "music-recording", "musical-notes", "scholarly-article", "poster", "video", "item", "recording", "archive", "article")
            start_date: Start date in format YYYYMMDD (optional)
            end_date: End date in format YYYYMMDD (optional)
            creator: Creator/author name to search by (optional)
            availability: Availability type (e.g., "online_resources", "all_items") (optional)
            institution: Institution code (default: "NNL")
            scope: Scope name (default: "NNL")
            start_index: Index of the first result to return (default: 1)
            page_size: Number of results to return (default: 10)

        Returns:
            Formatted search results with links to retrievable images when available
        """
        try:
            # Create search parameters
            params = SearchParams(
                institution=institution,
                scope_name=scope,
                start_index=start_index,
                page_size=page_size,
            )

            # Add main query
            params.add_query(SearchField.ANY, PrecisionOperator.CONTAINS, query)

            # Add optional filters
            if creator:
                params.add_query(
                    SearchField.CREATOR, PrecisionOperator.CONTAINS, creator
                )

            # Add date range if provided
            if start_date and end_date:
                params.add_date_range(start_date, end_date)
            elif start_date:
                params.add_query(
                    SearchField.DATE_RANGE_START, PrecisionOperator.EXACT, start_date
                )
            elif end_date:
                params.add_query(
                    SearchField.DATE_RANGE_END, PrecisionOperator.EXACT, end_date
                )

            # Add resource type if provided
            if resource_type:
                try:
                    # Try to convert string to ResourceType enum
                    resource_enum = ResourceType(resource_type.lower())
                    params.add_resource_type(resource_enum)
                except ValueError:
                    # If not a valid enum value, add as a query parameter
                    params.add_query(
                        FacetField.RESOURCE_TYPE,
                        PrecisionOperator.CONTAINS,
                        resource_type,
                    )

            # Add availability filter if provided
            if availability:
                try:
                    # Try to convert string to AvailabilityType enum
                    availability_enum = AvailabilityType(availability.lower())
                    params.add_query(
                        FacetField.AVAILABILITY,
                        PrecisionOperator.EXACT,
                        availability_enum.value,
                    )
                except ValueError:
                    # If not a valid enum value, add as a query parameter
                    params.add_query(
                        FacetField.AVAILABILITY, PrecisionOperator.EXACT, availability
                    )

            # Perform the search
            results = await self.search_client.search(params)

            # Process and format the results, including extracting image information
            return self._format_search_results_with_images(results)

        except ApiClientError as e:
            return f"Error searching catalog: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    # IIIF-related tools
    async def get_image_info(self, identifier: str) -> str:
        """
        Get information about an image using the IIIF Image Information API.

        Args:
            identifier: Image identifier

        Returns:
            Formatted image information
        """
        try:
            image_info = await self.iiif_client.get_image_info(identifier)

            # Format the image information
            info_lines = [
                f"Image Information for {identifier}:",
                f"Dimensions: {image_info.width} x {image_info.height} pixels",
                f"Protocol: {image_info.protocol}",
            ]

            if image_info.tile_width and image_info.tile_height:
                info_lines.append(
                    f"Tile Size: {image_info.tile_width} x {image_info.tile_height} pixels"
                )

            if image_info.max_width:
                info_lines.append(f"Maximum Width: {image_info.max_width} pixels")

            if image_info.max_height:
                info_lines.append(f"Maximum Height: {image_info.max_height} pixels")

            if image_info.max_area:
                info_lines.append(f"Maximum Area: {image_info.max_area} pixels")

            info_lines.append("\nRights Information:")

            if image_info.license:
                info_lines.append(f"License: {image_info.license}")

            if image_info.attribution:
                info_lines.append(f"Attribution: {image_info.attribution}")

            if image_info.logo:
                info_lines.append(f"Logo: {image_info.logo}")

            return "\n".join(info_lines)
        except ApiClientError as e:
            return f"Error getting image information: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    async def get_image(
        self,
        identifier: str,
        region: str = "full",
        size: str = "max",
        rotation: str = "0",
        quality: str = "default",
        image_format: str = "jpg",
    ) -> Image:
        """
        Get an image using the IIIF Image API.

        Args:
            identifier: Image identifier
            region: Region parameter (default: "full")
            size: Size parameter (default: "max")
            rotation: Rotation parameter (default: "0")
            quality: Image quality (default: "default")
            image_format: Image format (default: "jpg")

        Returns:
            The actual image as an Image object
        """
        try:
            # Get the image data from the IIIF client
            image_data = await self.iiif_client.get_image_data(
                identifier,
                region,
                size,
                rotation,
                Quality(quality),
                Format(image_format),
            )

            # Return the image data as an Image object
            return Image(data=image_data, format="jpeg")
            # return Image(data=image_data, format=image_format)

        except ApiClientError as e:
            raise ApiClientError(f"Error retrieving image: {str(e)}")

    async def get_tiled_image_urls(self, identifier: str, tile_size: int = 256) -> str:
        """
        Get URLs for retrieving a large image as tiles.

        Args:
            identifier: Image identifier
            tile_size: Size of each tile in pixels (default: 256)

        Returns:
            URLs for retrieving the image tiles
        """
        try:
            # Get image information
            image_info = await self.iiif_client.get_image_info(identifier)

            # Generate tile parameters
            tiles = self.iiif_client.generate_tiles(image_info, tile_size)

            # Format the tile URLs
            tile_lines = [
                f"Tiled Image URLs for {identifier}:",
                f"Image Dimensions: {image_info.width} x {image_info.height} pixels",
                f"Number of Tiles: {len(tiles)}",
                "",
            ]

            # Include at most 10 tile URLs in the response
            max_tiles_to_include = 10
            for i, (region, size, rotation, url) in enumerate(
                tiles[:max_tiles_to_include]
            ):
                tile_lines.append(f"Tile {i + 1}: {url}")

            if len(tiles) > max_tiles_to_include:
                tile_lines.append("...")
                tile_lines.append(
                    f"(Additional {len(tiles) - max_tiles_to_include} tiles not shown)"
                )

            return "\n".join(tile_lines)
        except ApiClientError as e:
            return f"Error getting tiled image URLs: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    # Helper methods
    def _format_search_results_with_images(self, results: Dict[str, Any]) -> str:
        """
        Format search results for display, including image URLs when available.

        Args:
            results: Search results from the API

        Returns:
            Formatted search results with image information
        """
        if not results:
            return "Error formatting search results: no results."
        try:
            # Extract total hits
            segments = results.get("SEGMENTS", {})
            jagroot = segments.get("JAGROOT", {})
            result = jagroot.get("RESULT", {})
            docset = result.get("DOCSET", {})
            total_hits = docset.get("@TOTALHITS", "0")
            docs = docset.get("DOC", [])

            # Format the results
            result_lines = [f"Found {total_hits} results:"]

            for i, doc in enumerate(docs):
                result_lines.append("")  # Add blank line between results

                # Extract document information
                primo_bib = doc.get("PrimoNMBib", {})
                record = primo_bib.get("record", {})
                control = record.get("control", {})
                display = record.get("display", {})

                # Extract basic metadata
                record_id = control.get("recordid", "Unknown ID")
                title = display.get("title", "Untitled")
                creator = display.get("creator", "Unknown Creator")
                doc_type = display.get("type", "Unknown Type")
                date = display.get("creationdate", "Unknown Date")

                # Add document information to result lines
                result_lines.append(f"Result {i + 1}:")
                result_lines.append(f"Title: {title}")
                result_lines.append(f"Creator: {creator}")
                result_lines.append(f"Type: {doc_type}")
                result_lines.append(f"Date: {date}")
                result_lines.append(f"ID: {record_id}")

                # Extract image information if available
                image_info = extract_image_info(record)
                if image_info["is_online"]:
                    result_lines.append("Available online: Yes")

                    if image_info["document_ids"]:
                        result_lines.append("IIIF Image IDs:")
                        for j, img_id in enumerate(
                            image_info["document_ids"][:3]
                        ):  # Limit to first 3 IDs
                            result_lines.append(f"  - {img_id}")
                            url = self.iiif_client.build_image_url(
                                img_id, "full", "max", "0"
                            )
                            result_lines.append(f"Link: {url}")
                        if len(image_info["document_ids"]) > 3:
                            result_lines.append(
                                f"  (and {len(image_info['document_ids']) - 3} more)"
                            )
                else:
                    result_lines.append("Available online: No")

            return "\n".join(result_lines)
        except Exception as e:
            # In case of error parsing the results, return a generic message
            return f"Error formatting search results: {str(e)}"
