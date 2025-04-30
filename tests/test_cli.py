"""
Tests for the CLI commands in nli_mcp_server.cli
"""

import json

from pytest import MonkeyPatch
from typer.testing import CliRunner

from nli_mcp_server.cli import app

# Create a runner object to invoke the CLI commands
runner = CliRunner()


# Helper function to create a mock async response
def mock_async_response(data):
    """Create an async mock function that returns the specified data."""

    async def mock_func(*args, **kwargs):
        return data

    # Set the name to avoid the __name__ attribute error
    mock_func.__name__ = f"mock_async_{id(data)}"
    return mock_func


# Test search command
class TestSearchCommand:
    def test_search_command_basic(self, monkeypatch: MonkeyPatch):
        # Mock the NliMcpServer.search_catalog method
        mock_result = {
            "SEGMENTS": {
                "JAGROOT": {
                    "RESULT": {
                        "DOCSET": {
                            "@TOTALHITS": "42",
                            "DOC": [
                                {
                                    "PrimoNMBib": {
                                        "record": {
                                            "control": {"recordid": "test_id_1"},
                                            "display": {
                                                "title": "Test Title 1",
                                                "creator": "Test Creator",
                                                "type": "Book",
                                                "creationdate": "2020",
                                                "format": "Text",
                                                "language": "English",
                                                "delivery": {
                                                    "availabilityLinksUrl": True
                                                },
                                            },
                                        }
                                    }
                                }
                            ],
                        }
                    }
                }
            }
        }

        # Apply the monkeypatch
        import nli_mcp_server.server

        monkeypatch.setattr(
            nli_mcp_server.server.NliMcpServer,
            "search_catalog",
            mock_async_response(mock_result),
        )

        # Call the CLI command
        result = runner.invoke(app, ["search", "test query"])

        # Verify the result
        assert result.exit_code == 0
        assert "42" in result.stdout
        assert "Test Title 1" in result.stdout
        assert "Test Creator" in result.stdout
        assert "Book" in result.stdout


    def test_search_command_with_options(self, monkeypatch: MonkeyPatch):
        # Mock the NliMcpServer.search_catalog method
        mock_result = {
            "SEGMENTS": {
                "JAGROOT": {
                    "RESULT": {
                        "DOCSET": {
                            "@TOTALHITS": "5",
                            "DOC": [
                                {
                                    "PrimoNMBib": {
                                        "record": {
                                            "control": {"recordid": "test_id_1"},
                                            "display": {
                                                "title": "Filtered Result",
                                                "creator": "Test Creator",
                                                "type": "Book",
                                                "creationdate": "2020",
                                                "format": "Text",
                                                "language": "English",
                                                "delivery": {
                                                    "availabilityLinksUrl": True
                                                },
                                            },
                                        }
                                    }
                                }
                            ],
                        }
                    }
                }
            }
        }

        # Apply the monkeypatch
        import nli_mcp_server.server

        monkeypatch.setattr(
            nli_mcp_server.server.NliMcpServer,
            "search_catalog",
            mock_async_response(mock_result),
        )

        # Call the CLI command with various options
        result = runner.invoke(
            app,
            [
                "search",
                "test query",
                "--rtype",
                "book",
                "--availability",
                "online_resources",
                "--creator",
                "Test Creator",
                "--start-date",
                "20200101",
                "--end-date",
                "20201231",
                "--start-index",
                "1",
                "--limit",
                "5",
            ],
        )

        # Verify the result
        assert result.exit_code == 0
        assert "5" in result.stdout
        assert "test_id_1" in result.stdout

    def test_search_command_error(self, monkeypatch: MonkeyPatch):
        # Mock the NliMcpServer.search_catalog method to raise an exception
        async def mock_error(*args, **kwargs):
            raise Exception("Test error")

        # Apply the monkeypatch
        import nli_mcp_server.server

        monkeypatch.setattr(
            nli_mcp_server.server.NliMcpServer, "search_catalog", mock_error
        )

        # Call the CLI command
        result = runner.invoke(app, ["search", "test query"])

        # Verify the result
        assert result.exit_code == 1
        assert "Error: Test error" in result.stdout


# Test image command
class TestImageCommand:
    def test_image_info_command(self, monkeypatch: MonkeyPatch):
        # Mock the IiifApiClient.get_image_info method
        from nli_mcp_server.api_models import ImageInfo

        mock_image_info = ImageInfo(
            identifier="test_id",
            protocol="http://iiif.io/api/image",
            width=1000,
            height=800,
            tile_width=256,
            tile_height=256,
            max_width=2000,
            max_height=2000,
            max_area=4000000,
            profile=[],
            license="https://creativecommons.org/licenses/by/4.0/",
            attribution="National Library of Israel",
            logo="https://example.com/logo.png",
        )

        # Apply the monkeypatch
        import nli_mcp_server.api_client

        monkeypatch.setattr(
            nli_mcp_server.api_client.IiifApiClient,
            "get_image_info",
            mock_async_response(mock_image_info),
        )

        # Call the CLI command
        result = runner.invoke(app, ["image", "test_id", "--info"])

        # Verify the result
        assert result.exit_code == 0
        assert "Image Information for test_id:" in result.stdout
        assert "Dimensions: 1000 x 800 pixels" in result.stdout
        assert "Protocol: http://iiif.io/api/image" in result.stdout
        assert "Tile Size: 256 x 256 pixels" in result.stdout
        assert "Maximum Width: 2000 pixels" in result.stdout
        assert "Maximum Height: 2000 pixels" in result.stdout
        assert "Maximum Area: 4000000 pixels" in result.stdout
        assert "License: https://creativecommons.org/licenses/by/4.0/" in result.stdout
        assert "Attribution: National Library of Israel" in result.stdout
        assert "Logo: https://example.com/logo.png" in result.stdout

    def test_image_url_command(self, monkeypatch: MonkeyPatch):
        # Mock the IiifApiClient.build_image_url method
        def mock_build_image_url(self, identifier, region, size, rotation):
            return f"https://iiif.nli.org.il/image/{identifier}/{region}/{size}/{rotation}/default.jpg"

        # Apply the monkeypatch
        import nli_mcp_server.api_client

        monkeypatch.setattr(
            nli_mcp_server.api_client.IiifApiClient,
            "build_image_url",
            mock_build_image_url,
        )

        # Call the CLI command
        result = runner.invoke(app, ["image", "test_id", "--width", "500"])

        # Verify the result
        assert result.exit_code == 0
        assert "Image URL:" in result.stdout
        assert "https://iiif.nli.org.il/image/test_id/" in result.stdout

    def test_image_command_error(self, monkeypatch: MonkeyPatch):
        # Mock the IiifApiClient.get_image_info method to raise an exception
        async def mock_error(*args, **kwargs):
            from nli_mcp_server.api_client import ApiClientError

            raise ApiClientError("Test error")

        # Apply the monkeypatch
        import nli_mcp_server.api_client

        monkeypatch.setattr(
            nli_mcp_server.api_client.IiifApiClient, "get_image_info", mock_error
        )

        # Call the CLI command
        result = runner.invoke(app, ["image", "test_id", "--info"])

        # Verify the result
        assert result.exit_code == 1
        assert "Error: Test error" in result.stdout


# Test tiles command
class TestTilesCommand:
    def test_tiles_command(self, monkeypatch: MonkeyPatch):
        # Mock the IiifApiClient.get_image_info method
        from nli_mcp_server.api_models import ImageInfo

        mock_image_info = ImageInfo(
            identifier="test_id",
            protocol="http://iiif.io/api/image",
            profile=[],
            width=1000,
            height=800,
            tile_width=256,
            tile_height=256,
        )

        # Mock the IiifApiClient.generate_tiles method
        def mock_generate_tiles(self, image_info, tile_size):
            return [
                (
                    "0,0,256,256",
                    "256,256",
                    "0",
                    "https://iiif.nli.org.il/image/test_id/0,0,256,256/256,256/0/default.jpg",
                ),
                (
                    "256,0,256,256",
                    "256,256",
                    "0",
                    "https://iiif.nli.org.il/image/test_id/256,0,256,256/256,256/0/default.jpg",
                ),
                (
                    "0,256,256,256",
                    "256,256",
                    "0",
                    "https://iiif.nli.org.il/image/test_id/0,256,256,256/256,256/0/default.jpg",
                ),
            ]

        # Apply the monkeypatches
        import nli_mcp_server.api_client

        monkeypatch.setattr(
            nli_mcp_server.api_client.IiifApiClient,
            "get_image_info",
            mock_async_response(mock_image_info),
        )
        monkeypatch.setattr(
            nli_mcp_server.api_client.IiifApiClient,
            "generate_tiles",
            mock_generate_tiles,
        )

        # Call the CLI command
        result = runner.invoke(app, ["tiles", "test_id"])

        # Verify the result
        assert result.exit_code == 0
        assert "Tiled Image URLs for test_id:" in result.stdout
        assert "Image Dimensions: 1000 x 800 pixels" in result.stdout
        assert "Number of Tiles: 3" in result.stdout
        assert (
            "Tile 1: https://iiif.nli.org.il/image/test_id/0,0,256,256/256,256/0/default.jpg"
            in result.stdout
        )
        assert (
            "Tile 2: https://iiif.nli.org.il/image/test_id/256,0,256,256/256,256/0/default.jpg"
            in result.stdout
        )
        assert (
            "Tile 3: https://iiif.nli.org.il/image/test_id/0,256,256,256/256,256/0/default.jpg"
            in result.stdout
        )

    def test_tiles_command_error(self, monkeypatch: MonkeyPatch):
        # Mock the IiifApiClient.get_image_info method to raise an exception
        async def mock_error(*args, **kwargs):
            from nli_mcp_server.api_client import ApiClientError

            raise ApiClientError("Test error")

        # Apply the monkeypatch
        import nli_mcp_server.api_client

        monkeypatch.setattr(
            nli_mcp_server.api_client.IiifApiClient, "get_image_info", mock_error
        )

        # Call the CLI command
        result = runner.invoke(app, ["tiles", "test_id"])

        # Verify the result
        assert result.exit_code == 1
        assert "Error: Test error" in result.stdout
