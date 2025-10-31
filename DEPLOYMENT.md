# Deployment Guide

This guide covers deploying Nadlan-MCP as an MCP server for AI agents.

## Prerequisites

- Python 3.10 or higher
- pip package manager
- MCP-compatible client (Claude Desktop, etc.)

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd nadlan-mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
# Test the library
python -c "from nadlan_mcp.govmap import GovmapClient; print('✓ Installation successful')"

# Test the MCP server
python run_fastmcp_server.py
```

## Deployment Options

### Option 1: Claude Desktop (Recommended)

Add to your Claude Desktop MCP configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nadlan-mcp": {
      "command": "python",
      "args": ["/absolute/path/to/nadlan-mcp/run_fastmcp_server.py"],
      "env": {}
    }
  }
}
```

**Important:** Use absolute paths, not relative paths.

Restart Claude Desktop to load the server.

### Option 2: Custom MCP Client

Use stdio transport to connect:

```python
import asyncio
from mcp.client.stdio import stdio_client

async def main():
    async with stdio_client([
        "python",
        "/path/to/nadlan-mcp/run_fastmcp_server.py"
    ]) as client:
        # List available tools
        result = await client.list_tools()
        print("Tools:", [t.name for t in result.tools])

        # Call a tool
        result = await client.call_tool(
            "find_recent_deals_for_address",
            {"address": "רוטשילד 1 תל אביב", "years_back": 2}
        )
        print(result)

asyncio.run(main())
```

### Option 3: Direct Python Usage

Use as a library without MCP:

```python
from nadlan_mcp.govmap import GovmapClient

client = GovmapClient()
deals = client.find_recent_deals_for_address("תל אביב רוטשילד 1", years_back=2)
print(f"Found {len(deals)} deals")
```

## Configuration

### Environment Variables

Create `.env` file (optional):

```bash
# API Settings
GOVMAP_BASE_URL=https://www.govmap.gov.il/api/
GOVMAP_USER_AGENT=NadlanMCP/2.0.0

# Timeouts (seconds)
GOVMAP_CONNECT_TIMEOUT=10
GOVMAP_READ_TIMEOUT=30

# Retry Settings
GOVMAP_MAX_RETRIES=3
GOVMAP_RETRY_MIN_WAIT=1
GOVMAP_RETRY_MAX_WAIT=10

# Rate Limiting
GOVMAP_REQUESTS_PER_SECOND=5.0

# Performance
GOVMAP_MAX_POLYGONS=10
```

### Programmatic Configuration

```python
from nadlan_mcp.config import GovmapConfig, set_config

config = GovmapConfig(
    connect_timeout=15,
    read_timeout=45,
    max_retries=5,
    requests_per_second=3.0
)
set_config(config)
```

## Verification

### Test MCP Tools

In Claude Desktop or your MCP client, try:

```
Find recent real estate deals for רוטשילד 1 תל אביב
```

Or use the test script:

```bash
python -m pytest tests/e2e/test_mcp_tools.py -v
```

### Check Logs

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

### Server Won't Start

**Problem:** `ImportError` or `ModuleNotFoundError`

**Solution:**
```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Verify Python version
python --version  # Should be 3.10+
```

### Claude Desktop Not Finding Server

**Problem:** Server doesn't appear in Claude Desktop

**Solution:**
1. Check config file path is correct for your OS
2. Use **absolute paths** in configuration
3. Restart Claude Desktop after config changes
4. Check Claude Desktop logs for errors

### API Errors

**Problem:** `requests.exceptions.ConnectionError`

**Solution:**
- Check internet connection
- Verify Govmap API is accessible: `curl https://www.govmap.gov.il/api/`
- Check firewall/proxy settings

**Problem:** `429 Too Many Requests`

**Solution:**
- Reduce `GOVMAP_REQUESTS_PER_SECOND` (default: 5)
- Add delays between requests

### No Results Found

**Problem:** `No deals found for this address`

**Solution:**
- Use Hebrew address format: "רוטשילד 1 תל אביב"
- Increase search radius (default: 50m)
- Extend time period: `years_back=5`

## Performance Optimization

### For Production Use

1. **Increase timeouts** for slow networks:
   ```bash
   GOVMAP_READ_TIMEOUT=60
   ```

2. **Adjust rate limiting** based on your needs:
   ```bash
   GOVMAP_REQUESTS_PER_SECOND=3.0  # More conservative
   ```

3. **Limit polygon queries** to improve speed:
   ```bash
   GOVMAP_MAX_POLYGONS=5  # Fewer API calls
   ```

### Monitoring

```python
import logging

# Enable info logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Updates

### Updating Nadlan-MCP

```bash
cd nadlan-mcp
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

Restart your MCP client to load the updated server.

## Security Considerations

1. **No API Keys Required:** Govmap API is public, no authentication needed
2. **Rate Limiting:** Built-in to respect API limits
3. **Input Validation:** All user inputs are validated before API calls
4. **No Data Storage:** No user data is stored or cached

## Support

- **Issues:** Create issue at repository
- **Documentation:** See README.md, ARCHITECTURE.md
- **Examples:** See `examples/` directory

---

**Note:** Nadlan-MCP uses the public Israeli government Govmap API. Please respect rate limits and terms of service.
