from unittest.mock import ANY, AsyncMock, MagicMock, patch

import httpx
import pytest

from nli_mcp_server.api_client import (
    ApiClientError,
    IiifApiClient,
    SearchApiClient,
)
from nli_mcp_server.api_models import (
    Format,
    ImageInfo,
    PrecisionOperator,
    Quality,
    ResourceType,
    SearchField,
    SearchParams,
)


@pytest.fixture
def search_params():
    """Create a fixture for search parameters"""
    params = SearchParams(page_size=10)
    params.add_query(SearchField.ANY, PrecisionOperator.CONTAINS, "Jerusalem")
    params.add_resource_type(ResourceType.MAP)
    return params


@pytest.fixture
def search_response_json():
    """Mock search response data"""
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
                                            "type": "map",
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
                                            "type": "photograph",
                                        },
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
def image_info_response_json():
    """Mock image info response data"""
    return {
        "@context": "http://iiif.io/api/image/2/context.json",
        "@id": "http://iiif.nli.org.il/IIIFv21/FL7070748",
        "protocol": "http://iiif.io/api/image",
        "width": 1000,
        "height": 800,
        "tiles": [{"width": 256, "height": 256}],
        "profile": ["http://iiif.io/api/image/2/level2.json"],
        "attribution": "Test Attribution",
        "license": "http://creativecommons.org/licenses/by-nc-sa/4.0/",
    }


@pytest.fixture
def image_info():
    """Create an ImageInfo fixture"""
    return ImageInfo(
        identifier="FL7070748",
        width=1000,
        height=800,
        protocol="http://iiif.io/api/image",
        profile=[],
        tile_width=256,
        tile_height=256,
        license="http://creativecommons.org/licenses/by-nc-sa/4.0/",
        attribution="Test Attribution",
    )


@pytest.mark.asyncio
async def test_search_api_client_search(search_params, search_response_json):
    """Test SearchApiClient.search method"""
    # Mock the httpx.AsyncClient.get method to return a response with our test data
    mock_response = MagicMock()
    mock_response.json.return_value = search_response_json
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        client = SearchApiClient()
        result = await client.search(search_params)

        # Verify the result matches our mock response
        assert result == search_response_json

        # Verify httpx.AsyncClient.get was called with the expected URL
        httpx.AsyncClient.get.assert_called_once_with(ANY)

        # Check that the URL contains the expected query parameters
        url = httpx.AsyncClient.get.call_args[0][0]
        assert "institution=NNL" in url
        assert "bulkSize=10" in url
        assert "query=" in url
        assert "query_inc=" in url


@pytest.mark.asyncio
async def test_search_api_client_search_http_error():
    """Test SearchApiClient.search method when HTTP error occurs"""
    # Create a search params object
    params = SearchParams(page_size=10)
    params.add_query(SearchField.ANY, PrecisionOperator.CONTAINS, "Jerusalem")

    # Mock the httpx.AsyncClient.get method to raise an HTTPStatusError
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Error", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        client = SearchApiClient()

        # Verify that ApiClientError is raised
        with pytest.raises(ApiClientError) as excinfo:
            await client.search(params)

        # Check the error message
        assert "HTTP error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_search_api_client_search_request_error():
    """Test SearchApiClient.search method when request error occurs"""
    # Create a search params object
    params = SearchParams(page_size=10)
    params.add_query(SearchField.ANY, PrecisionOperator.CONTAINS, "Jerusalem")

    # Mock the httpx.AsyncClient.get method to raise a RequestError
    with patch(
        "httpx.AsyncClient.get",
        AsyncMock(side_effect=httpx.RequestError("Error", request=MagicMock())),
    ):
        client = SearchApiClient()

        # Verify that ApiClientError is raised
        with pytest.raises(ApiClientError) as excinfo:
            await client.search(params)

        # Check the error message
        assert "Request error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_search_api_client_extract_record_ids(search_response_json):
    """Test SearchApiClient.extract_record_ids method"""
    client = SearchApiClient()
    record_ids = await client.extract_record_ids(search_response_json)

    # Verify the extracted record IDs
    assert len(record_ids) == 2
    assert "test_record_id_1" in record_ids
    assert "test_record_id_2" in record_ids


@pytest.mark.asyncio
async def test_search_api_client_extract_record_ids_empty():
    """Test SearchApiClient.extract_record_ids method with empty results"""
    client = SearchApiClient()
    record_ids = await client.extract_record_ids({})

    # Verify that an empty list is returned
    assert record_ids == []


@pytest.mark.asyncio
async def test_iiif_api_client_get_image_info(image_info_response_json):
    """Test IiifApiClient.get_image_info method"""
    # Mock the httpx.AsyncClient.get method to return a response with our test data
    mock_response = MagicMock()
    mock_response.json.return_value = image_info_response_json
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        client = IiifApiClient()
        image_info = await client.get_image_info("FL7070748")

        # Verify the image info object
        assert image_info.identifier == "FL7070748"
        assert image_info.width == 1000
        assert image_info.height == 800
        assert image_info.protocol == "http://iiif.io/api/image"
        assert image_info.tile_width == 256
        assert image_info.tile_height == 256
        assert image_info.license == "http://creativecommons.org/licenses/by-nc-sa/4.0/"
        assert image_info.attribution == "Test Attribution"

        # Verify httpx.AsyncClient.get was called with the expected URL
        expected_url = "http://iiif.nli.org.il/IIIFv21/FL7070748/info.json"
        httpx.AsyncClient.get.assert_called_once_with(expected_url)


@pytest.mark.asyncio
async def test_iiif_api_client_get_image_info_http_error():
    """Test IiifApiClient.get_image_info method when HTTP error occurs"""
    # Mock the httpx.AsyncClient.get method to raise an HTTPStatusError
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Error", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        client = IiifApiClient()

        # Verify that ApiClientError is raised
        with pytest.raises(ApiClientError) as excinfo:
            await client.get_image_info("FL7070748")

        # Check the error message
        assert "HTTP error" in str(excinfo.value)


def test_iiif_api_client_build_image_url():
    """Test IiifApiClient.build_image_url method"""
    client = IiifApiClient()

    # Test with default parameters
    url = client.build_image_url("FL7070748", "full", "max", "0")
    assert url == "http://iiif.nli.org.il/IIIFv21/FL7070748/full/max/0/default.jpg"

    # Test with custom parameters
    url = client.build_image_url(
        "FL7070748", "pct:10,20,30,40", "200,", "90", Quality.GRAY, Format.JPG
    )
    assert (
        url
        == "http://iiif.nli.org.il/IIIFv21/FL7070748/pct:10,20,30,40/200,/90/gray.jpg"
    )


@pytest.mark.asyncio
async def test_iiif_api_client_get_image_data():
    """Test IiifApiClient.get_image_data method"""
    # Mock image data
    mock_image_data = b"test_image_data"

    # Mock the httpx.AsyncClient.get method to return a response with our test data
    mock_response = MagicMock()
    mock_response.content = mock_image_data
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        client = IiifApiClient()
        image_data = await client.get_image_data("FL7070748")

        # Verify the image data
        assert image_data == mock_image_data

        # Verify httpx.AsyncClient.get was called with the expected URL
        expected_url = "http://iiif.nli.org.il/IIIFv21/FL7070748/full/max/0/default.jpg"
        httpx.AsyncClient.get.assert_called_once_with(expected_url)


@pytest.mark.asyncio
async def test_iiif_api_client_get_image_data_http_error():
    """Test IiifApiClient.get_image_data method when HTTP error occurs"""
    # Mock the httpx.AsyncClient.get method to raise an HTTPStatusError
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Error", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        client = IiifApiClient()

        # Verify that ApiClientError is raised
        with pytest.raises(ApiClientError) as excinfo:
            await client.get_image_data("FL7070748")

        # Check the error message
        assert "HTTP error" in str(excinfo.value)


def test_iiif_api_client_generate_tiles(image_info):
    """Test IiifApiClient.generate_tiles method"""
    client = IiifApiClient()
    tiles = client.generate_tiles(image_info, 256)

    # Verify the number of tiles
    # For 1000x800 image with 256x256 tiles, we should have 4x4=16 tiles
    assert len(tiles) == 16

    # Verify the structure of a tile
    first_tile = tiles[0]
    assert len(first_tile) == 4
    region, size, rotation, url = first_tile

    # Verify the region format (should be a percentage region)
    assert region.startswith("pct:")

    # Verify the size format (should be a width specification)
    assert size.endswith(",")

    # Verify the rotation (should be "0")
    assert rotation == "0"

    # Verify the URL format
    assert url.startswith("http://iiif.nli.org.il/IIIFv21/FL7070748/pct:")
    assert "/256,/0/default.jpg" in url


def test_iiif_api_client_generate_tiles_small_image(image_info):
    """Test IiifApiClient.generate_tiles method with an image smaller than the tile size"""
    # Modify the image info to have a small size
    image_info.width = 200
    image_info.height = 150

    client = IiifApiClient()
    tiles = client.generate_tiles(image_info, 256)

    # Verify that only one tile is generated
    assert len(tiles) == 1

    # Verify the structure of the tile
    region, size, rotation, url = tiles[0]

    # Since the image is smaller than the tile size, the region should cover the whole image
    assert region == "pct:0.0,0.0,100.0,100.0"
