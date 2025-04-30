"""
Data models for API interactions with the National Library of Israel APIs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class PrecisionOperator(str, Enum):
    """Precision operators for search API queries."""

    CONTAINS = "contains"
    EXACT = "exact"
    BEGINS_WITH = "begins_with"
    INCLUDES = "include"


class SearchField(str, Enum):
    """Available search fields for the NLI Search API."""

    ANY = "any"
    TITLE = "title"
    DESCRIPTION = "desc"
    CREATOR = "creator"
    SUBJECT = "sub"
    DATE_RANGE_START = "dr_s"
    DATE_RANGE_END = "dr_e"


class FacetField(str, Enum):
    """Available facet fields for filtering in the NLI Search API."""

    LANGUAGE = "facet_lang"
    CREATOR = "facet_creator"
    RESOURCE_TYPE = "facet_rtype"
    TOPIC = "facet_topic"
    CREATION_DATE = "facet_creationdate"
    FORMAT = "facet_fmt"
    AVAILABILITY = "facet_tlevel"


class ResourceType(str, Enum):
    """Available resource types for filtering in the NLI Search API."""

    BOOK = "book"
    PHOTOGRAPH = "photograph"
    PERIODICAL = "periodical"
    MANUSCRIPT = "manuscript"
    MAP = "map"
    ETHNOGRAPHIC_RECORDING = "ethnographic-recording"
    RADIO_RECORDING = "radio-recording"
    MUSIC_RECORDING = "music-recording"
    MUSICAL_NOTES = "musical-notes"
    SCHOLARLY_ARTICLE = "scholarly-article"
    POSTER = "poster"
    VIDEO = "video"
    ITEM = "item"
    RECORDING = "recording"
    ARCHIVE = "archive"
    ARTICLE = "article"


class AvailabilityType(str, Enum):
    """Available availability options for filtering in the NLI Search API."""

    # ONLINE_ACCESS = "online_access"
    ONLINE_RESOURCES = "online_resources"
    ALL_ITEMS = "all_items"
    # ONLINE_AND_API_ACCESS = "online_and_api_access"
    # ONLINE_ACCESS_NO_API = "online_access_no_api"
    # ONLINE_IN_LIBRARY_ONLY = "online_in_library_only"
    # NO_ONLINE_ACCESS = "no_online_access"


@dataclass
class SearchQuery:
    """
    Represents a single search query parameter for the NLI Search API.

    Example: `any,contains,Jerusalem`
    """

    field: Union[SearchField, FacetField]
    precision: PrecisionOperator
    value: str

    def to_query_param(self) -> str:
        """Convert to the format expected by the API."""
        return f"{self.field.value},{self.precision.value},{self.value}"


@dataclass
class SearchParams:
    """Parameters for the NLI Search API."""

    institution: str = "NNL"
    scope_name: str = "NNL"
    queries: List[SearchQuery] = field(default_factory=list)
    start_index: int = 1
    page_size: int = 50
    json_format: bool = True
    rtype: List[ResourceType] = field(default_factory=list)
    creator: List[str] = field(default_factory=list)

    def add_query(
        self,
        field: Union[SearchField, FacetField],
        precision: PrecisionOperator,
        value: str,
    ) -> None:
        """Add a query parameter to the search."""
        self.queries.append(SearchQuery(field, precision, value))

    def add_date_range(self, start_date: str, end_date: str) -> None:
        """
        Add date range parameters to the search query.

        Args:
            start_date: Start date in format YYYYMMDD
            end_date: End date in format YYYYMMDD
        """
        self.add_query(
            SearchField.DATE_RANGE_START, PrecisionOperator.EXACT, start_date
        )
        self.add_query(SearchField.DATE_RANGE_END, PrecisionOperator.EXACT, end_date)

    def add_resource_type(self, resource_type: ResourceType) -> None:
        """Add a resource type to filter the search results."""
        if resource_type not in self.rtype:
            self.rtype.append(resource_type)


@dataclass
class ImageInfo:
    """Information about an image from the IIIF Image Information API."""

    identifier: str
    width: int
    height: int
    protocol: str
    profile: List[str]
    tile_width: Optional[int] = None
    tile_height: Optional[int] = None
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    max_area: Optional[int] = None
    license: Optional[str] = None
    attribution: Optional[str] = None
    logo: Optional[str] = None

    @classmethod
    def from_json(cls, identifier: str, data: Dict[str, Any]) -> "ImageInfo":
        """
        Create an ImageInfo instance from the JSON response.

        Args:
            identifier: The image identifier
            data: The JSON data from the info.json response

        Returns:
            An ImageInfo instance
        """
        # Extract profile information
        max_width = None
        max_height = None
        max_area = None

        for profile_item in data.get("profile", []):
            if isinstance(profile_item, dict):
                if "maxWidth" in profile_item:
                    max_width = profile_item["maxWidth"]
                if "maxHeight" in profile_item:
                    max_height = profile_item["maxHeight"]
                if "maxArea" in profile_item:
                    max_area = profile_item["maxArea"]

        # Extract tile information if available
        tile_width = None
        tile_height = None

        if "tiles" in data and len(data["tiles"]) > 0:
            tiles = data["tiles"][0]
            tile_width = tiles.get("width")
            tile_height = tiles.get(
                "height", tile_width
            )  # Default to width if height not specified

        return cls(
            identifier=identifier,
            width=data.get("width", 0),
            height=data.get("height", 0),
            protocol=data.get("protocol", ""),
            profile=[p if isinstance(p, str) else "" for p in data.get("profile", [])],
            tile_width=tile_width,
            tile_height=tile_height,
            max_width=max_width,
            max_height=max_height,
            max_area=max_area,
            license=data.get("license"),
            attribution=data.get("attribution"),
            logo=data.get("logo"),
        )


class Region:
    """
    Represents a region parameter for IIIF Image API.

    Can be either:
    - "full" to get the entire image
    - "x,y,w,h" to get a specific region in pixels
    - "pct:x,y,w,h" to get a specific region in percentages
    """

    @staticmethod
    def full() -> str:
        """Get the full image."""
        return "full"

    @staticmethod
    def pixels(x: int, y: int, width: int, height: int) -> str:
        """
        Get a region by pixel coordinates.

        Args:
            x: X-coordinate of the top-left corner
            y: Y-coordinate of the top-left corner
            width: Width of the region
            height: Height of the region

        Returns:
            Region parameter string
        """
        return f"{x},{y},{width},{height}"

    @staticmethod
    def percentage(x: float, y: float, width: float, height: float) -> str:
        """
        Get a region by percentage coordinates.

        Args:
            x: X-coordinate percentage of the top-left corner (0-100)
            y: Y-coordinate percentage of the top-left corner (0-100)
            width: Width percentage of the region (0-100)
            height: Height percentage of the region (0-100)

        Returns:
            Region parameter string
        """
        return f"pct:{x},{y},{width},{height}"


class Size:
    """
    Represents a size parameter for IIIF Image API.
    """

    @staticmethod
    def width(width: int) -> str:
        """
        Set the width while maintaining the aspect ratio.

        Args:
            width: Width in pixels

        Returns:
            Size parameter string
        """
        return f"{width},"

    @staticmethod
    def height(height: int) -> str:
        """
        Set the height while maintaining the aspect ratio.

        Args:
            height: Height in pixels

        Returns:
            Size parameter string
        """
        return f",{height}"

    @staticmethod
    def full() -> str:
        """
        Set the dimensions as full image.

        Returns the full image.

        Returns:
            Size parameter string
        """
        return "max"

    @staticmethod
    def max_dimensions(width: int, height: int) -> str:
        """
        Set the maximum dimensions while maintaining aspect ratio.

        Returns the largest image that fits within the width and height constraints.

        Args:
            width: Maximum width in pixels
            height: Maximum height in pixels

        Returns:
            Size parameter string
        """
        return f"!{width},{height}"

    @staticmethod
    def exact(width: int, height: int) -> str:
        """
        Set exact dimensions (may distort image).

        Args:
            width: Width in pixels
            height: Height in pixels

        Returns:
            Size parameter string
        """
        return f"{width},{height}"


class Rotation:
    """
    Represents a rotation parameter for IIIF Image API.
    """

    @staticmethod
    def none() -> str:
        """No rotation."""
        return "0"

    @staticmethod
    def degrees(degrees: int) -> str:
        """
        Rotate the image by the specified number of degrees.

        Args:
            degrees: Rotation angle in degrees (typically 0, 90, 180, or 270)

        Returns:
            Rotation parameter string
        """
        return str(degrees)

    @staticmethod
    def mirrored(degrees: int = 0) -> str:
        """
        Mirror the image horizontally and then rotate by the specified degrees.

        Args:
            degrees: Rotation angle in degrees (typically 0, 90, 180, or 270)

        Returns:
            Rotation parameter string
        """
        return f"!{degrees}"


class Quality(str, Enum):
    """Available quality parameters for IIIF Image API."""

    DEFAULT = "default"
    GRAY = "gray"


class Format(str, Enum):
    """Available format parameters for IIIF Image API."""

    JPG = "jpg"
