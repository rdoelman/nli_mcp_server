"""
Command-line interface for interacting with the National Library of Israel APIs.

This module provides a simple CLI for searching the NLI catalog and retrieving images.
"""

import asyncio
from enum import Enum
from functools import wraps
from typing import Optional

import typer
from typing_extensions import Annotated

from nli_mcp_server.api_client import (
    ApiClientError,
    IiifApiClient,
)
from nli_mcp_server.api_models import (
    AvailabilityType,
    Rotation,
    Size,
)
from nli_mcp_server.server import NliMcpServer


# Helper function to run async commands with typer
def async_command_wrapper(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


app = typer.Typer(help="National Library of Israel API client")


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


@app.command()
@async_command_wrapper
async def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    rtype: Annotated[
        Optional[str],
        typer.Option(help="Type of resources to search for"),
    ] = None,
    availability: Annotated[
        AvailabilityType, typer.Option(help="Availability type to filter by")
    ] = AvailabilityType.ALL_ITEMS,
    creator: Annotated[
        Optional[str], typer.Option(help="Filter by creator name")
    ] = None,
    start_date: Annotated[
        Optional[str], typer.Option(help="Start date in format YYYYMMDD")
    ] = None,
    end_date: Annotated[
        Optional[str], typer.Option(help="End date in format YYYYMMDD")
    ] = None,
    start_index: Annotated[int, typer.Option(help="Starting index for pagination")] = 1,
    limit: Annotated[
        int, typer.Option(help="Maximum number of results to return")
    ] = 10,
):
    """Search the NLI catalog with advanced filtering options"""
    server = NliMcpServer()

    try:
        # Use the server's search_catalog method with all parameters
        results = await server.search_catalog(
            query=query,
            resource_type=rtype,
            availability=availability.value.lower()
            if availability != AvailabilityType.ALL_ITEMS
            else None,
            creator=creator,
            start_date=start_date,
            end_date=end_date,
            start_index=start_index,
            page_size=limit,
        )

        print(results)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
@async_command_wrapper
async def image(
    identifier: Annotated[str, typer.Argument(help="Image identifier")],
    info: Annotated[
        bool, typer.Option(help="Get image information instead of URL")
    ] = False,
    width: Annotated[
        Optional[int], typer.Option(help="Width of the image in pixels")
    ] = None,
    height: Annotated[
        Optional[int], typer.Option(help="Height of the image in pixels")
    ] = None,
    region: Annotated[
        str,
        typer.Option(
            help="Region parameter (e.g., 'full', '0,0,100,100', 'pct:0,0,50,50')"
        ),
    ] = "full",
    rotation: Annotated[int, typer.Option(help="Rotation angle in degrees")] = 0,
    mirror: Annotated[bool, typer.Option(help="Mirror the image horizontally")] = False,
):
    """Get image information or URL"""
    client = IiifApiClient()

    try:
        if info:
            # Get image information
            image_info = await client.get_image_info(identifier)

            # Print the image information
            print(f"Image Information for {identifier}:")
            print(f"Dimensions: {image_info.width} x {image_info.height} pixels")
            print(f"Protocol: {image_info.protocol}")

            if image_info.tile_width and image_info.tile_height:
                print(
                    f"Tile Size: {image_info.tile_width} x {image_info.tile_height} pixels"
                )

            if image_info.max_width:
                print(f"Maximum Width: {image_info.max_width} pixels")

            if image_info.max_height:
                print(f"Maximum Height: {image_info.max_height} pixels")

            if image_info.max_area:
                print(f"Maximum Area: {image_info.max_area} pixels")

            print("\nRights Information:")

            if image_info.license:
                print(f"License: {image_info.license}")

            if image_info.attribution:
                print(f"Attribution: {image_info.attribution}")

            if image_info.logo:
                print(f"Logo: {image_info.logo}")
        else:
            # Build image URL
            # Create size parameter
            if width is None and height is None:
                # raise ValueError("Either width or height must be specified.")
                size = Size.full()
                print(size)
            elif height is None:
                size = Size.width(width)
            else:
                size = Size.exact(width, height)

            # Create rotation parameter
            if mirror:
                rotation_param = Rotation.mirrored(rotation)
            else:
                rotation_param = Rotation.degrees(rotation)

            # Build the URL
            url = client.build_image_url(identifier, region, size, rotation_param)

            print(f"Image URL: {url}")
    except ApiClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
@async_command_wrapper
async def tiles(
    identifier: Annotated[str, typer.Argument(help="Image identifier")],
    tile_size: Annotated[int, typer.Option(help="Size of each tile in pixels")] = 256,
):
    """Get tiled image URLs"""
    client = IiifApiClient()

    try:
        # Get image information
        image_info = await client.get_image_info(identifier)

        # Generate tile parameters
        tiles = client.generate_tiles(image_info, tile_size)

        # Print the tile information
        print(f"Tiled Image URLs for {identifier}:")
        print(f"Image Dimensions: {image_info.width} x {image_info.height} pixels")
        print(f"Number of Tiles: {len(tiles)}")
        print()

        # Display at most 10 tile URLs
        max_tiles_to_display = 10
        for i, (region, size, rotation, url) in enumerate(tiles[:max_tiles_to_display]):
            print(f"Tile {i + 1}: {url}")

        if len(tiles) > max_tiles_to_display:
            print("...")
            print(f"(Additional {len(tiles) - max_tiles_to_display} tiles not shown)")
    except ApiClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


def main():
    """Main entry point for the CLI."""

    app()


if __name__ == "__main__":
    main()
