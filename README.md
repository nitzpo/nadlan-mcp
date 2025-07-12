# Israel Real Estate MCP

A Python-based Mission Control Program (MCP) for interacting with the Israeli government's public real estate data API (Govmap). This project provides both a Python library and an MCP server that allows real estate agents, professionals, and AI agents to query recent property deals, analyze market trends, and retrieve detailed real estate information.

## Description

This project provides a comprehensive Python interface to the Israeli government's Govmap API, enabling users to:

- Search for property addresses using autocomplete
- Find geographical coordinates for addresses
- Retrieve block (Gush) and parcel (Helka) information
- Query recent real estate deals by location
- Get detailed street and neighborhood deal information
- Analyze market trends in specific areas

## Features

- **Address Autocomplete**: Search for addresses using free text and get precise coordinates
- **Geospatial Data**: Retrieve block and parcel information for any coordinate point
- **Deal Discovery**: Find real estate deals within a specified radius of any location
- **Street Analysis**: Get detailed deal information for specific streets
- **Neighborhood Insights**: Analyze deals within entire neighborhoods
- **Time-based Filtering**: Search for deals within specific date ranges
- **Comprehensive Search**: High-level function that combines all features to find deals for any address
- **Error Handling**: Robust error handling for network issues and API failures
- **Logging**: Detailed logging for debugging and monitoring

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd nadlan-mcp
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### MCP Server (Recommended for AI Agents)

The project includes an MCP (Model Context Protocol) server that allows AI agents to access Israeli real estate data. The server provides multiple deployment options:

#### 1. FastMCP Server (Recommended)

**NEW: Using FastMCP for better compatibility and reliability**

```bash
python run_fastmcp_server.py
```

This starts the FastMCP server which resolves compatibility issues with the standard MCP library.

#### 2. Interactive Demo Server

For testing and demonstration purposes:

```bash
python simple_mcp_server.py
```

This runs an interactive demo where you can test the tools directly in the terminal.

#### 3. Full MCP Server (Legacy)

For production use with MCP clients:

```bash
python run_mcp_server.py
```

This starts the full MCP server that can be connected to by MCP-compatible clients.

#### 4. Direct Server Module

You can also run the server directly:

```bash
python -m nadlan_mcp.simple_fastmcp_server
```

#### MCP Client Configuration

To connect to the server from MCP clients, use the following configuration:

**For Claude Desktop or other MCP clients (FastMCP - Recommended):**

Add to your MCP client configuration:

```json
{
  "servers": {
    "nadlan-mcp": {
      "command": "python",
      "args": ["/path/to/nadlan-mcp/run_fastmcp_server.py"],
      "env": {}
    }
  }
}
```

**Alternative (Legacy MCP Server):**

```json
{
  "servers": {
    "nadlan-mcp": {
      "command": "python",
      "args": ["/path/to/nadlan-mcp/run_mcp_server.py"],
      "env": {}
    }
  }
}
```

**For development with stdio transport (FastMCP):**

```python
import asyncio
from mcp.client.stdio import stdio_client

async def main():
    async with stdio_client(["python", "run_fastmcp_server.py"]) as client:
        # List available tools
        result = await client.list_tools()
        print("Available tools:", result.tools)
        
        # Call a tool
        result = await client.call_tool("find_recent_deals_for_address", {
            "address": "סוקולוב 38 חולון",
            "years_back": 2
        })
        print("Results:", result)

asyncio.run(main())
```

#### Available MCP Tools

**FastMCP Server provides these 5 tools:**
- 🏠 `find_recent_deals_for_address` - Main comprehensive analysis tool
- 📊 `get_deals_by_radius` - Find deals within a radius of coordinates
- 🏘️ `get_street_deals` - Get deals for a specific street polygon
- 🔍 `autocomplete_address` - Address search and validation
- 📈 `compare_addresses` - Compare multiple addresses

**Legacy MCP Server provides these 4 tools:**

##### 🏠 `find_recent_deals_for_address`
**Main comprehensive analysis tool**
- **Description**: Find all relevant real estate deals for a given address
- **Parameters**: 
  - `address` (required): The address to search for (Hebrew or English)
  - `years_back` (optional): Number of years to look back (default: 2)
- **Returns**: List of deals with detailed information

**Example usage:**
```json
{
  "address": "בן יהודה 1 תל אביב",
  "years_back": 3
}
```

##### 📊 `analyze_market_trends`
**Market trend analysis with price insights**
- **Description**: Analyze price trends and market data for an address
- **Parameters**:
  - `address` (required): The address to analyze
  - `years_back` (optional): Number of years to analyze (default: 2)
- **Returns**: Market analysis with trends, average prices, and insights

**Example usage:**
```json
{
  "address": "דיזנגוף 50 תל אביב",
  "years_back": 5
}
```

##### 🏘️ `compare_neighborhoods`
**Compare multiple areas**
- **Description**: Compare real estate data across multiple addresses or neighborhoods
- **Parameters**:
  - `addresses` (required): List of addresses to compare
  - `years_back` (optional): Number of years to analyze (default: 2)
- **Returns**: Comparative analysis with rankings and insights

**Example usage:**
```json
{
  "addresses": ["סוקולוב 38 חולון", "בן יהודה 1 תל אביב", "דיזנגוף 50 תל אביב"],
  "years_back": 2
}
```

##### 🔍 `autocomplete_address`
**Address search and validation**
- **Description**: Search for and validate Israeli addresses
- **Parameters**:
  - `search_text` (required): The address text to search for
- **Returns**: List of matching addresses with coordinates

**Example usage:**
```json
{
  "search_text": "רוטשילד תל אביב"
}
```

#### Server Features

- **Async Operations**: All tools run asynchronously for better performance
- **Error Handling**: Comprehensive error handling with meaningful error messages
- **Logging**: Detailed logging for debugging and monitoring
- **Data Validation**: Input validation and sanitization
- **Hebrew Support**: Full support for Hebrew addresses and text

#### Testing the Server

You can test the server using the interactive demo:

```bash
python simple_mcp_server.py
```

This will start an interactive session where you can:
1. List available tools
2. Call tools with parameters
3. See formatted results
4. Test error handling

#### Server Logs

The server provides detailed logging. To see debug information:

```bash
# Set logging level before running
export PYTHONPATH=/path/to/nadlan-mcp
python -c "import logging; logging.basicConfig(level=logging.DEBUG)" run_mcp_server.py
```

#### Troubleshooting

**Connection Issues:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that Python path is correct in client configuration
- Verify the server starts without errors

**Tool Execution Issues:**
- Check network connectivity for API calls
- Verify address format (Hebrew addresses work best)
- Review server logs for detailed error information

**Performance:**
- Use appropriate `years_back` values (2-5 years recommended)
- Large radius searches may take longer
- Consider caching results for repeated queries

### Python Library Usage

```python
from nadlan_mcp import GovmapClient

# Initialize the client
client = GovmapClient()

# Search for recent deals for a specific address
address = "סוקולוב 38 חולון"
deals = client.find_recent_deals_for_address(address, years_back=2)

print(f"Found {len(deals)} deals for {address}")
for deal in deals[:5]:  # Show first 5 deals
    print(f"Address: {deal.get('address')}")
    print(f"Date: {deal.get('dealDate')}")
    print(f"Price: {deal.get('price')}")
    print("---")
```

### Advanced Usage Examples

#### 1. Address Autocomplete

```python
from nadlan_mcp import GovmapClient

client = GovmapClient()

# Search for an address
result = client.autocomplete_address("בן יהודה 1 תל אביב")
if result['results']:
    best_match = result['results'][0]
    print(f"Found: {best_match.get('displayName')}")
    print(f"Coordinates: {best_match.get('point')}")
```

#### 2. Get Block and Parcel Information

```python
# Get coordinates from address first
autocomplete_result = client.autocomplete_address("דיזנגוף 50 תל אביב")
point = tuple(autocomplete_result['results'][0]['point'])

# Get block and parcel info
gush_helka = client.get_gush_helka(point)
print(f"Block/Parcel info: {gush_helka}")
```

#### 3. Find Deals by Radius

```python
# Find deals within 100 meters of a point
point = (3870923.95, 3766288.07)  # Example coordinates
deals = client.get_deals_by_radius(point, radius=100)

print(f"Found {len(deals)} deals within 100m")
for deal in deals:
    print(f"- {deal.get('address')}: {deal.get('price')}")
```

#### 4. Street-specific Deals

```python
# Get detailed street deals for a specific polygon
polygon_id = "52190246"
street_deals = client.get_street_deals(
    polygon_id, 
    limit=10, 
    start_date="2023-01", 
    end_date="2024-01"
)

print(f"Found {len(street_deals)} street deals")
```

#### 5. Neighborhood Analysis

```python
# Get neighborhood deals
neighborhood_deals = client.get_neighborhood_deals(
    polygon_id="52282030",
    limit=20,
    start_date="2023-01",
    end_date="2024-01"
)

print(f"Found {len(neighborhood_deals)} neighborhood deals")
```

### Running the Example Script

The project includes a main example script that demonstrates basic usage:

```bash
python -m nadlan_mcp.main
```

Or run it directly:

```bash
python nadlan_mcp/main.py
```

## API Reference

### GovmapClient Class

The main class for interacting with the Govmap API.

#### Methods

##### `__init__(base_url: str = "https://www.govmap.gov.il/api/")`
Initialize the client with the base API URL.

##### `autocomplete_address(search_text: str) -> Dict[str, Any]`
Search for addresses using autocomplete functionality.

- **Parameters:**
  - `search_text`: The address to search for (Hebrew or English)
- **Returns:** Dictionary with search results and coordinates
- **Raises:** `requests.RequestException`, `ValueError`

##### `get_gush_helka(point: Tuple[float, float]) -> Dict[str, Any]`
Get block (Gush) and parcel (Helka) information for coordinates.

- **Parameters:**
  - `point`: Tuple of (longitude, latitude)
- **Returns:** Dictionary with block and parcel data
- **Raises:** `requests.RequestException`, `ValueError`

##### `get_deals_by_radius(point: Tuple[float, float], radius: int = 50) -> List[Dict[str, Any]]`
Find deals within a specified radius of a point.

- **Parameters:**
  - `point`: Tuple of (longitude, latitude)
  - `radius`: Search radius in meters (default: 50)
- **Returns:** List of deal dictionaries
- **Raises:** `requests.RequestException`

##### `get_street_deals(polygon_id: str, limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]`
Get detailed deals for a specific street.

- **Parameters:**
  - `polygon_id`: The polygon ID for the street
  - `limit`: Maximum number of deals to return (default: 10)
  - `start_date`: Start date in 'YYYY-MM' format
  - `end_date`: End date in 'YYYY-MM' format
- **Returns:** List of detailed deal information
- **Raises:** `requests.RequestException`

##### `get_neighborhood_deals(polygon_id: str, limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]`
Get deals within the same neighborhood.

- **Parameters:**
  - `polygon_id`: The polygon ID for the area
  - `limit`: Maximum number of deals to return (default: 10)
  - `start_date`: Start date in 'YYYY-MM' format
  - `end_date`: End date in 'YYYY-MM' format
- **Returns:** List of neighborhood deals
- **Raises:** `requests.RequestException`

##### `find_recent_deals_for_address(address: str, years_back: int = 2) -> List[Dict[str, Any]]`
**Main function**: Find all relevant deals for an address (combines all other methods).

- **Parameters:**
  - `address`: The address to search for
  - `years_back`: How many years back to search (default: 2)
- **Returns:** List of all relevant deals, sorted by date
- **Raises:** `ValueError`, `requests.RequestException`

## Govmap API Endpoints

This project uses the following Govmap API endpoints:

- **Autocomplete**: `POST /search-service/autocomplete`
- **Entities by Point**: `POST /layers-catalog/entitiesByPoint`
- **Deals by Radius**: `GET /real-estate/deals/{point}/{radius}`
- **Street Deals**: `GET /real-estate/street-deals/{polygon_id}`
- **Neighborhood Deals**: `GET /real-estate/neighborhood-deals/{polygon_id}`

### API Base URL
```
https://www.govmap.gov.il/api/
```

## Error Handling

The client includes comprehensive error handling:

- **Network Errors**: Handles connection issues and API timeouts
- **API Errors**: Manages HTTP error responses and invalid data
- **Data Validation**: Validates API responses and handles missing data
- **Logging**: Provides detailed logging for debugging issues

## Logging

The project uses Python's built-in logging module. To enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Dependencies

- **requests**: HTTP library for API calls
- **python-dotenv**: Environment variable management
- **mcp**: Model Context Protocol SDK for AI agent integration
- **pytest**: Testing framework

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Disclaimer

This tool is for educational and professional use only. Please respect the Govmap API terms of service and rate limits. The authors are not responsible for any misuse of this tool.

## Support

For issues, questions, or contributions, please create an issue in the repository.

---

**Note**: This project is not officially affiliated with the Israeli government or Govmap. It is an independent tool created to facilitate access to public real estate data.
