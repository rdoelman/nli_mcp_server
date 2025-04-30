"""
Enhanced tests for server.py to improve test coverage.
These tests focus on the previously untested functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp import Image

from nli_mcp_server.api_client import ApiClientError, IiifApiClient, SearchApiClient
from nli_mcp_server.api_models import (
    Format,
    ImageInfo,
    PrecisionOperator,
    Quality,
    ResourceType,
    SearchField,
    FacetField,
    SearchParams,
)
from nli_mcp_server.server import NliMcpServer, extract_image_info


@pytest.fixture
def rich_search_result_mock():
    """Mock search result data with more detailed structure"""
    return {
        "SEGMENTS": {
            "JAGROOT": {
                "RESULT": {
                    "DOCSET": {
                        "@TOTALHITS": "10",
                        "DOC": [
                            {
                                "PrimoNMBib": {
                                    "record": {
                                        "control": {"recordid": "test_record_id_1"},
                                        "display": {
                                            "title": "Test Title 1",
                                            "creator": "Test Creator 1",
                                            "type": "photograph",
                                            "creationdate": "1900",
                                        },
                                        "facets": {"toplevel": "online_resources"},
                                        "links": {
                                            "linktorsrc": [
                                                "https://example.com/view/resource?dps_pid=test_image_id_1&stream=true",
                                            ]
                                        },
                                    }
                                }
                            },
                            {
                                "PrimoNMBib": {
                                    "record": {
                                        "control": {"recordid": "test_record_id_2"},
                                        "display": {
                                            "title": "Test Title 2",
                                            "creator": "Test Creator 2",
                                            "type": "book",
                                            "creationdate": "1950",
                                        },
                                        "facets": {"toplevel": "physical_only"},
                                    }
                                }
                            },
                        ],
                    }
                }
            }
        }
    }


@pytest.fixture
def detailed_image_info_mock():
    """Mock image information data with more fields"""

    class ImageInfoMock:
        def __init__(self):
            self.identifier = "test_image_id"
            self.width = 2000
            self.height = 1500
            self.protocol = "http://iiif.io/api/image"
            self.profile = ["http://iiif.io/api/image/2/level2.json"]
            self.tile_width = 256
            self.tile_height = 256
            self.max_width = 3000
            self.max_height = 3000
            self.max_area = 9000000
            self.license = "https://creativecommons.org/licenses/by/4.0/"
            self.attribution = "National Library of Israel"
            self.logo = "https://example.com/logo.png"

    return ImageInfoMock()


@pytest.mark.asyncio
async def test_search_catalog_basic_query():
    """Test the search_catalog method with a basic query"""
    # Arrange
    server = NliMcpServer()
    expected_result = "Found 10 results:\n\nResult 1:\nTitle: Test Title 1\nCreator: Test Creator 1"

    # Set up the mock implementation of _format_search_results_with_images
    server._format_search_results_with_images = MagicMock(
        return_value=expected_result
    )

    # Set up the mock for search_client.search
    server.search_client.search = AsyncMock()

    # Act
    result = await server.search_catalog(query="Jerusalem")

    # Assert
    server.search_client.search.assert_called_once()
    assert result == expected_result

    # Verify the search parameters
    args, _ = server.search_client.search.call_args
    search_params = args[0]
    assert isinstance(search_params, SearchParams)
    assert search_params.institution == "NNL"
    assert search_params.scope_name == "NNL"

    # Verify the query parameters
    assert len(search_params.queries) == 1
    assert search_params.queries[0].field == SearchField.ANY
    assert search_params.queries[0].precision == PrecisionOperator.CONTAINS
    assert search_params.queries[0].value == "Jerusalem"


@pytest.mark.asyncio
async def test_search_catalog_with_filters():
    """Test the search_catalog method with various filters"""
    # Arrange
    server = NliMcpServer()
    expected_result = "Mock formatted search results"
    server._format_search_results_with_images = MagicMock(
        return_value=expected_result
    )
    server.search_client.search = AsyncMock()

    # Act
    result = await server.search_catalog(
        query="Jerusalem",
        resource_type="photograph",
        start_date="19000101",
        end_date="19501231",
        creator="Cohen",
        availability="online_resources",
        page_size=20,
    )

    # Assert
    server.search_client.search.assert_called_once()
    assert result == expected_result

    # Verify the search parameters
    args, _ = server.search_client.search.call_args
    search_params = args[0]

    # Check query parameters
    query_fields = [(q.field, q.precision, q.value) for q in search_params.queries]
    assert (SearchField.ANY, PrecisionOperator.CONTAINS, "Jerusalem") in query_fields
    assert (SearchField.CREATOR, PrecisionOperator.CONTAINS, "Cohen") in query_fields
    assert (
        SearchField.DATE_RANGE_START,
        PrecisionOperator.EXACT,
        "19000101",
    ) in query_fields
    assert (
        SearchField.DATE_RANGE_END,
        PrecisionOperator.EXACT,
        "19501231",
    ) in query_fields
    assert (
        FacetField.AVAILABILITY,
        PrecisionOperator.EXACT,
        "online_resources",
    ) in query_fields

    # Check resource type
    assert len(search_params.rtype) == 1
    assert search_params.rtype[0] == ResourceType.PHOTOGRAPH

    # Check pagination
    assert search_params.page_size == 20


@pytest.mark.asyncio
async def test_search_catalog_handles_errors():
    """Test that search_catalog properly handles exceptions"""
    # Arrange
    server = NliMcpServer()
    server.search_client.search = AsyncMock(
        side_effect=ApiClientError("API connection failed")
    )

    # Act
    result = await server.search_catalog(query="Jerusalem")

    # Assert
    assert "Error searching catalog" in result
    assert "API connection failed" in result


@pytest.mark.asyncio
async def test_get_image_info_complete():
    """Test the get_image_info method returns formatted complete information"""
    # Arrange
    server = NliMcpServer()
    image_info = ImageInfo(
        identifier="test_image_id",
        width=2000,
        height=1500,
        protocol="http://iiif.io/api/image",
        profile=["http://iiif.io/api/image/2/level2.json"],
        tile_width=256,
        tile_height=256,
        max_width=3000,
        max_height=3000,
        max_area=9000000,
        license="https://creativecommons.org/licenses/by/4.0/",
        attribution="National Library of Israel",
        logo="https://example.com/logo.png",
    )
    server.iiif_client.get_image_info = AsyncMock(return_value=image_info)

    # Act
    result = await server.get_image_info("test_image_id")

    # Assert
    server.iiif_client.get_image_info.assert_called_once_with("test_image_id")
    assert "Image Information for test_image_id" in result
    assert "Dimensions: 2000 x 1500 pixels" in result
    assert "Protocol: http://iiif.io/api/image" in result
    assert "Tile Size: 256 x 256 pixels" in result
    assert "Maximum Width: 3000 pixels" in result
    assert "Maximum Height: 3000 pixels" in result
    assert "Maximum Area: 9000000 pixels" in result
    assert "License: https://creativecommons.org/licenses/by/4.0/" in result
    assert "Attribution: National Library of Israel" in result
    assert "Logo: https://example.com/logo.png" in result


@pytest.mark.asyncio
async def test_get_image_info_minimal():
    """Test the get_image_info method with minimal image information"""
    # Arrange
    server = NliMcpServer()
    image_info = ImageInfo(
        identifier="minimal_image",
        width=1000,
        height=800,
        protocol="http://iiif.io/api/image",
        profile=["http://iiif.io/api/image/2/level1.json"],
    )
    server.iiif_client.get_image_info = AsyncMock(return_value=image_info)

    # Act
    result = await server.get_image_info("minimal_image")

    # Assert
    server.iiif_client.get_image_info.assert_called_once_with("minimal_image")
    assert "Image Information for minimal_image" in result
    assert "Dimensions: 1000 x 800 pixels" in result
    assert "Protocol: http://iiif.io/api/image" in result
    # Check that optional fields are not mentioned
    assert "Tile Size" not in result
    assert "Maximum Width" not in result
    assert "License" not in result


@pytest.mark.asyncio
async def test_get_image_info_handles_errors():
    """Test that get_image_info properly handles exceptions"""
    # Arrange
    server = NliMcpServer()
    server.iiif_client.get_image_info = AsyncMock(
        side_effect=ApiClientError("Image not found")
    )

    # Act
    result = await server.get_image_info("nonexistent_image")

    # Assert
    assert "Error getting image information" in result
    assert "Image not found" in result


@pytest.mark.asyncio
async def test_get_image_success():
    """Test successfully retrieving an image"""
    # Arrange
    server = NliMcpServer()
    image_data = b"mock image data"
    server.iiif_client.get_image_data = AsyncMock(return_value=image_data)

    # Act
    result = await server.get_image(
        identifier="test_image_id",
        region="full",
        size="max",
        rotation="0",
        quality="default",
        image_format="jpg",
    )

    # Assert
    server.iiif_client.get_image_data.assert_called_once_with(
        "test_image_id", "full", "max", "0", Quality.DEFAULT, Format.JPG
    )
    assert isinstance(result, Image)
    assert result.data == image_data
    assert result._format == "jpeg"


@pytest.mark.asyncio
async def test_get_image_error():
    """Test error handling when retrieving an image"""
    # Arrange
    server = NliMcpServer()
    server.iiif_client.get_image_data = AsyncMock(
        side_effect=ApiClientError("Image not available")
    )

    # Act/Assert
    with pytest.raises(ApiClientError) as excinfo:
        await server.get_image("nonexistent_image")

    assert "Error retrieving image" in str(excinfo.value)
    assert "Image not available" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_tiled_image_urls():
    """Test the get_tiled_image_urls method"""
    # Arrange
    server = NliMcpServer()

    # Create a mock image info object
    image_info = MagicMock()
    image_info.identifier = "test_image_id"
    image_info.width = 1000
    image_info.height = 800

    # Set up mocks
    server.iiif_client.get_image_info = AsyncMock(return_value=image_info)
    server.iiif_client.generate_tiles = MagicMock(
        return_value=[
            ("pct:0,0,25,25", "256,", "0", "http://example.com/tile1"),
            ("pct:25,0,25,25", "256,", "0", "http://example.com/tile2"),
            ("pct:50,0,25,25", "256,", "0", "http://example.com/tile3"),
            ("pct:75,0,25,25", "256,", "0", "http://example.com/tile4"),
            ("pct:0,25,25,25", "256,", "0", "http://example.com/tile5"),
            ("pct:25,25,25,25", "256,", "0", "http://example.com/tile6"),
            ("pct:50,25,25,25", "256,", "0", "http://example.com/tile7"),
            ("pct:75,25,25,25", "256,", "0", "http://example.com/tile8"),
            ("pct:0,50,25,25", "256,", "0", "http://example.com/tile9"),
            ("pct:25,50,25,25", "256,", "0", "http://example.com/tile10"),
            ("pct:50,50,25,25", "256,", "0", "http://example.com/tile11"),
            ("pct:75,50,25,25", "256,", "0", "http://example.com/tile12"),
            ("pct:0,75,25,25", "256,", "0", "http://example.com/tile13"),
            ("pct:25,75,25,25", "256,", "0", "http://example.com/tile14"),
            ("pct:50,75,25,25", "256,", "0", "http://example.com/tile15"),
            ("pct:75,75,25,25", "256,", "0", "http://example.com/tile16"),
        ]
    )

    # Act
    result = await server.get_tiled_image_urls("test_image_id", 256)

    # Assert
    server.iiif_client.get_image_info.assert_called_once_with("test_image_id")
    server.iiif_client.generate_tiles.assert_called_once_with(image_info, 256)

    # Check that the result contains the expected information
    assert "Tiled Image URLs for test_image_id" in result
    assert "Image Dimensions: 1000 x 800 pixels" in result
    assert "Number of Tiles: 16" in result
    assert "Tile 1: http://example.com/tile1" in result
    assert "Tile 10: http://example.com/tile10" in result
    assert "(Additional 6 tiles not shown)" in result


@pytest.mark.asyncio
async def test_get_tiled_image_urls_handles_errors():
    """Test that get_tiled_image_urls properly handles exceptions"""
    # Arrange
    server = NliMcpServer()
    server.iiif_client.get_image_info = AsyncMock(
        side_effect=ApiClientError("Image info not available")
    )

    # Act
    result = await server.get_tiled_image_urls("nonexistent_image")

    # Assert
    assert "Error getting tiled image URLs" in result
    assert "Image info not available" in result


def test_extract_image_info_complex():
    """Test the extract_image_info function with a complex data structure"""
    record_data = {
        "facets": {"toplevel": "online_resources"},
        "delivery": {"delcategory": "Online Resource"},
        "links": {
            "linktorsrc": [
                "https://example.com/view/resource?dps_pid=test_id_1&stream=true",
                "https://example.com/view/resource?dps_pid=test_id_2&stream=true",
            ],
            "linktohtml": ["https://example.com/terms-of-use"],
            "linktopdf": [
                "https://example.com/view/resource?dps_pid=test_id_3&stream=true"
            ],
        },
        "nested": {
            "deeply": {
                "nested": {
                    "urls": [
                        "https://example.com/view/resource?dps_pid=test_id_4&stream=true"
                    ]
                }
            }
        },
    }

    # Extract image info
    image_info = extract_image_info(record_data)

    # Verify results
    assert image_info["is_online"]
    assert len(image_info["urls"]) == 4  # Should find 4 URLs (terms-of-use is filtered)
    assert "https://example.com/terms-of-use" not in image_info["urls"]
    assert len(image_info["document_ids"]) == 4
    assert "test_id_1" in image_info["document_ids"]
    assert "test_id_2" in image_info["document_ids"]
    assert "test_id_3" in image_info["document_ids"]
    assert "test_id_4" in image_info["document_ids"]


def test_extract_image_info_invalid_input():
    """Test the extract_image_info function with invalid inputs"""
    # Test with None input
    result = extract_image_info(None)
    assert result["urls"] == []
    assert result["document_ids"] == []
    assert not result["is_online"]

    # Test with non-dict input
    result = extract_image_info("not a dict")
    assert result["urls"] == []
    assert result["document_ids"] == []
    assert not result["is_online"]

    # Test with empty dict
    result = extract_image_info({})
    assert result["urls"] == []
    assert result["document_ids"] == []
    assert not result["is_online"]


def test_format_search_results_with_images(rich_search_result_mock):
    """Test the _format_search_results_with_images method"""
    server = NliMcpServer()

    # Mock the iiif_client.build_image_url method
    server.iiif_client.build_image_url = MagicMock(
        return_value="https://example.com/iiif/test_image_id_1/full/max/0/default.jpg"
    )

    # Call the method under test
    result = server._format_search_results_with_images(rich_search_result_mock)

    # Verify result contains expected information
    assert "Found 10 results:" in result
    assert "Result 1:" in result
    assert "Title: Test Title 1" in result
    assert "Creator: Test Creator 1" in result
    assert "Type: photograph" in result
    assert "Date: 1900" in result
    assert "ID: test_record_id_1" in result
    assert "Available online: Yes" in result
    assert "IIIF Image IDs:" in result
    assert "test_image_id_1" in result
    assert "https://example.com/iiif/test_image_id_1/full/max/0/default.jpg" in result

    assert "Result 2:" in result
    assert "Title: Test Title 2" in result
    assert "Available online: No" in result


def test_format_search_results_with_images_error_handling():
    """Test error handling in _format_search_results_with_images method"""
    server = NliMcpServer()

    # Test with invalid data structure
    result = server._format_search_results_with_images({})
    assert "Error formatting search results" in result

    # Test with unexpected structure
    malformed_data = {"SEGMENTS": {"JAGROOT": "not_a_dict"}}
    result = server._format_search_results_with_images(malformed_data)
    assert "Error formatting search results" in result


def test_nli_mcp_server_initialization():
    """Test that NliMcpServer initializes correctly"""
    server = NliMcpServer(server_name="custom_mcp")

    # Verify server properties
    assert server.name == "nli_mcp"
    assert server.mcp.name == "custom_mcp"
    assert isinstance(server.search_client, SearchApiClient)
    assert isinstance(server.iiif_client, IiifApiClient)

    # Verify tools are registered
    for method_name in [
        "search_catalog",
        "get_image_info",
        "get_image",
        "get_tiled_image_urls",
    ]:
        # Check if the method exists in server
        assert hasattr(server, method_name)


@patch("nli_mcp_server.server.FastMCP")
def test_register_tools(mock_fastmcp):
    """Test that tools are properly registered with the MCP server"""
    # Arrange
    mock_mcp = MagicMock()
    mock_fastmcp.return_value = mock_mcp
    
    # Act
    server = NliMcpServer()
    # Explicitly call the _register_tools method
    server._register_tools()
    
    # Assert - check that tool decorator was called
    assert mock_mcp.tool.call_count > 0  # Should be called at least once
    
    # Get the mock for the tool decorator
    mock_tool_decorator = mock_mcp.tool.return_value
    
    # Verify that the decorator was called for all four methods
    assert mock_tool_decorator.call_count >= 4  # At least once for each method
    
    # Get a list of all methods that were registered as tools
    registered_calls = mock_tool_decorator.call_args_list
    registered_methods = []
    for mock_call in registered_calls:
        if len(mock_call[0]) > 0 and hasattr(mock_call[0][0], "__name__"):
            registered_methods.append(mock_call[0][0].__name__)
    
    # Verify each required method was registered
    assert "search_catalog" in registered_methods
    assert "get_image_info" in registered_methods
    assert "get_image" in registered_methods
    assert "get_tiled_image_urls" in registered_methods


@patch("nli_mcp_server.server.FastMCP")
def test_run_method(mock_fastmcp):
    """Test the run method of NliMcpServer"""
    # Arrange
    mock_mcp = MagicMock()
    mock_fastmcp.return_value = mock_mcp
    server = NliMcpServer()
    
    # Act
    server.run()
    server.run("sse")
    
    # Assert
    assert mock_mcp.run.call_count == 2
    mock_mcp.run.assert_any_call(transport="stdio")
    mock_mcp.run.assert_any_call(transport="sse")