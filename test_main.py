"""
Unit tests for the perenual scraper functions.

Tests the extract_care_description function to ensure it correctly
extracts both labels and values from the plant species page HTML.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from playwright.async_api import async_playwright, Page, Locator
import main


class MockLocator:
    """Mock Playwright Locator for testing."""

    def __init__(self, elements=None):
        self._elements = elements or []
        self._current_index = 0

    async def count(self):
        """Return the number of elements."""
        return len(self._elements)

    def nth(self, index):
        """Return a locator for the nth element."""
        self._current_index = index
        if index < len(self._elements):
            return MockElementLocator(self._elements[index])
        return MockElementLocator({})

    async def inner_text(self):
        """Return inner text (for direct locator calls)."""
        return ""


class MockElementLocator:
    """Mock a single element locator for testing."""

    def __init__(self, data):
        self._data = data

    async def inner_text(self):
        """Return the inner text of this element."""
        return self._data.get("text", "")

    def locator(self, selector: str):
        """Return a new locator for the given selector."""
        # Handle child selectors
        if "h3" in selector:
            return MockElementLocator({"text": self._data.get("label", "")})
        elif "p" in selector:
            return MockElementLocator({"text": self._data.get("value", "")})
        return MockElementLocator({})


class MockPage:
    """Mock Playwright Page for testing."""

    def __init__(self, care_blocks=None):
        """
        Initialize mock page with care block data.

        Args:
            care_blocks: List of dicts with 'label' and 'value' keys
        """
        self._care_blocks = care_blocks or []

    def locator(self, selector: str):
        """Return a locator for the given selector."""
        if "rounded-md.shadow.p-3" in selector:
            return MockLocator(self._care_blocks)
        return MockLocator()


@pytest.mark.asyncio
async def test_extract_care_description_single_block():
    """Test extracting a single care description block."""
    # Arrange: Set up mock page with one care block
    mock_page = MockPage([
        {
            "label": "watering",
            "value": "Water your Pyramidalis Silver Fir when the soil appears dry to the touch."
        }
    ])

    # Act: Call the function
    result = await main.extract_care_description(mock_page)

    # Assert: Verify the result
    assert result == {
        "watering": "Water your Pyramidalis Silver Fir when the soil appears dry to the touch."
    }


@pytest.mark.asyncio
async def test_extract_care_description_multiple_blocks():
    """Test extracting multiple care description blocks."""
    # Arrange: Set up mock page with three care blocks (watering, sunlight, pruning)
    mock_page = MockPage([
        {
            "label": "watering",
            "value": "Water your Pyramidalis Silver Fir when the soil appears dry to the touch."
        },
        {
            "label": "sunlight",
            "value": "Pyramidalis Silver Fir Abies Alba 'Pyramidalis' will thrive in full sun."
        },
        {
            "label": "pruning",
            "value": "Pruning Pyramidalis Silver Fir Abies Alba 'Pyramidalis' should be done in late winter."
        }
    ])

    # Act: Call the function
    result = await main.extract_care_description(mock_page)

    # Assert: Verify all three care types are extracted
    assert len(result) == 3
    assert "watering" in result
    assert "sunlight" in result
    assert "pruning" in result
    assert "soil appears dry" in result["watering"]
    assert "full sun" in result["sunlight"]
    assert "late winter" in result["pruning"]


@pytest.mark.asyncio
async def test_extract_care_description_empty_page():
    """Test extracting from a page with no care blocks."""
    # Arrange: Set up mock page with no care blocks
    mock_page = MockPage([])

    # Act: Call the function
    result = await main.extract_care_description(mock_page)

    # Assert: Should return empty dict
    assert result == {}


@pytest.mark.asyncio
async def test_extract_care_description_whitespace_cleaning():
    """Test that leading/trailing whitespace is properly cleaned."""
    # Arrange: Set up mock page with whitespace in values
    mock_page = MockPage([
        {
            "label": "  WATERING  ",
            "value": "  Water your plant every 7-10 days.  "
        }
    ])

    # Act: Call the function
    result = await main.extract_care_description(mock_page)

    # Assert: Verify whitespace is cleaned and label is lowercased
    assert result["watering"] == "Water your plant every 7-10 days."


@pytest.mark.asyncio
async def test_extract_care_description_handles_missing_values():
    """Test that the function gracefully handles blocks with missing data."""
    # Arrange: Set up mock page with some blocks missing values
    mock_page = MockPage([
        {"label": "watering", "value": "Water when dry."},
        {"label": "", "value": "Some value"},  # Missing label
        {"label": "sunlight", "value": ""},   # Missing value
        {"label": "pruning", "value": "Prune in spring."},
    ])

    # Act: Call the function
    result = await main.extract_care_description(mock_page)

    # Assert: Should extract valid blocks and handle gracefully
    assert "watering" in result
    assert "pruning" in result
    assert result["watering"] == "Water when dry."
    assert result["pruning"] == "Prune in spring."


@pytest.mark.asyncio
async def test_extract_care_description_integration():
    """
    Integration test: Test against the actual Perenual website.

    This test makes a real HTTP request to perenual.com and tests
    the function against the actual HTML structure.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to the actual species page
            await page.goto("https://perenual.com/plant-species-database-search-finder/species/2")
            await page.wait_for_load_state("domcontentloaded")

            # Act: Call the real function with the real page
            result = await main.extract_care_description(page)

            # Assert: Verify we get the expected care types
            assert isinstance(result, dict), "Result should be a dictionary"
            assert len(result) > 0, "Should extract at least one care description"

            # The page should have at least these common care types
            expected_care_types = ["watering", "sunlight", "pruning"]
            for care_type in expected_care_types:
                if care_type in result:
                    assert len(result[care_type]) > 0, f"{care_type} should have non-empty description"
                    assert isinstance(result[care_type], str), f"{care_type} value should be a string"

            # Log what we found for debugging
            print(f"\nExtracted {len(result)} care descriptions: {list(result.keys())}")
            for key, value in result.items():
                print(f"  {key}: {value[:100]}...")

        finally:
            await browser.close()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
