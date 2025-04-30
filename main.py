"""
Main entry point for the National Library of Israel MCP server.

This module provides the main functionality for running the MCP server
and interacting with the National Library of Israel APIs.
"""

from nli_mcp_server.server import NliMcpServer

server = NliMcpServer(server_name="nli_mcp")

if __name__ == "__main__":
    mcp = server.mcp
    mcp.run(transport="sse")
