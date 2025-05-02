  # National Library of Israel MCP Server 🇮🇱📖🔍

  This package provides a Model Context Protocol (MCP) server that interfaces between large language models and the National Library of Israel's APIs. The MCP server allows AI assistants to search the NLI catalog, retrieve images, and access library resources programmatically.

  > ⚠️ **Important Note**: This is an independent, external initiative and is **not affiliated** with or endorsed by the National Library of Israel. This project is developed by enthusiasts to enhance AI accessibility to public library resources.

  ## Features

  * **Catalog Search**: Query the NLI catalog by various criteria including general terms, title, creator, date range
  * **IIIF Image Access**: Retrieve, manipulate and get detailed information about digitized materials
  * **Advanced Filtering**: Control search by resource type (photographs, maps, books etc.), online availability, date range, and creator
  * **Image Manipulation**: Support for different regions, sizes, rotations, and quality parameters
  * **Large Image Support**: Generate tiled image URLs for efficiently retrieving high-resolution images

  ## Tools

  * **search_catalog**
    * Search the NLI catalog with advanced filtering options
    * Inputs:
        * `query` (string): The main search query
        * `resource_type` (string, optional): Type of resource to search for (photograph, book, manuscript, etc.)
        * `start_date` (string, optional): Start date in format YYYYMMDD
        * `end_date` (string, optional): End date in format YYYYMMDD
        * `creator` (string, optional): Creator/author name to search by
        * `availability` (string, optional): Availability type (online_resources, all_items, etc.)
        * `page_size` (integer, optional): Number of results to return (default: 10)

  * **get_image_info**
    * Get information about an image using the IIIF Image Information API
    * Inputs:
        * `identifier` (string): Image identifier

  * **get_image**
    * Get an image using the IIIF Image API
    * Inputs:
        * `identifier` (string): Image identifier
        * `region` (string, optional): Region parameter (default: "full")
        * `size` (string, optional): Size parameter (default: "max")
        * `rotation` (string, optional): Rotation parameter (default: "0")
        * `quality` (string, optional): Image quality (default: "default")
        * `image_format` (string, optional): Image format (default: "jpg")

  * **get_tiled_image_urls**
    * Get URLs for retrieving a large image as tiles
    * Inputs:
        * `identifier` (string): Image identifier
        * `tile_size` (integer, optional): Size of each tile in pixels (default: 256)

  ## Installation

  ### Dependencies

  - Python 3.10 or higher
  - httpx
  - mcp >= 1.2.0
  - uv (recommended)

  For installing uv, please follow the instructions at [uv documentation](https://docs.astral.sh/uv/).

  To install this package from source, navigate to the project and run:

  ```bash
  uv sync
  ```

  ## Claude Desktop Integration

  To use this MCP server with Claude Desktop, add the following configuration to your `claude_desktop_config.json` file:

  ```json
  {
    "mcpServers": {
      "nli_mcp": {
        "command": "uv",
        "args": [
          "run",
          "--with",
          "mcp[cli]",
          "mcp",
          "run",
          "[PATH_TO_REPO]/nli_mcp_server/main.py"
        ]
      }
    }
  }
  ```

  Replace `[PATH_TO_REPO]` with the actual path to your checked out git repository.

  ## Development

  For development, use uv to run the server:

  ```bash
  # Start the server in development mode
  uv run mcp dev main.py
  ```

  ## License

  [MIT License](LICENSE)