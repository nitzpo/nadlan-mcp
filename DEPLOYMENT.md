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

### Option 4: Cloud Deployment (HTTP)

Deploy Nadlan-MCP as an HTTP service to cloud platforms like Render, Railway, or using Docker.

#### Prerequisites

- Docker installed (for Docker deployment)
- Render/Railway account (for cloud deployment)
- Git repository (for cloud deployment)

#### 4.1: Render Deployment

**Step 1:** Push your code to a Git repository (GitHub, GitLab, etc.)

**Step 2:** Create a new Web Service on Render:
- Go to https://dashboard.render.com
- Click "New +" → "Web Service"
- Connect your Git repository
- Configure:
  - **Name:** `nadlan-mcp` (or your preferred name)
  - **Environment:** `Docker`
  - **Region:** Choose closest to your users
  - **Branch:** `main` (or your default branch)
  - **Build Command:** (leave empty - Docker handles this)
  - **Start Command:** (leave empty - Docker CMD is used)

**Step 3:** Configure Environment Variables (optional):

In Render dashboard, add environment variables:
```
GOVMAP_MAX_RETRIES=3
GOVMAP_REQUESTS_PER_SECOND=5.0
GOVMAP_DEFAULT_YEARS_BACK=2
```

**Step 4:** Deploy
- Click "Create Web Service"
- Render will automatically build and deploy your Docker container
- Wait for deployment to complete (~2-5 minutes)

**Step 5:** Access Your Service
- Your service will be available at: `https://your-service-name.onrender.com`
- MCP endpoint: `https://your-service-name.onrender.com/mcp`
- Health check: `https://your-service-name.onrender.com/health`

**Important Notes:**
- Render's free tier may have cold starts (delays when service is idle)
- For production, use a paid plan for better performance
- The HTTP server runs on the port specified by Render's `PORT` environment variable

#### 4.2: Docker Deployment

**Build the Docker Image:**

```bash
docker build -t nadlan-mcp .
```

**Run Locally:**

```bash
# Run on default port 8000
docker run -p 8000:8000 nadlan-mcp

# Run on custom port
docker run -p 8080:8080 -e PORT=8080 nadlan-mcp

# Run with environment variables
docker run -p 8000:8000 \
  -e GOVMAP_MAX_RETRIES=5 \
  -e GOVMAP_REQUESTS_PER_SECOND=3.0 \
  nadlan-mcp
```

**Test the Deployment:**

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","service":"nadlan-mcp"}
```

**Push to Docker Registry (Optional):**

```bash
# Tag for Docker Hub
docker tag nadlan-mcp your-username/nadlan-mcp:latest

# Push to Docker Hub
docker push your-username/nadlan-mcp:latest

# Or use GitHub Container Registry
docker tag nadlan-mcp ghcr.io/your-username/nadlan-mcp:latest
docker push ghcr.io/your-username/nadlan-mcp:latest
```

#### 4.3: Railway Deployment

**Step 1:** Install Railway CLI (optional) or use web dashboard

```bash
npm install -g @railway/cli
railway login
```

**Step 2:** Deploy from CLI:

```bash
railway init
railway up
```

**Or via Web Dashboard:**
- Go to https://railway.app
- Click "New Project" → "Deploy from GitHub repo"
- Select your repository
- Railway auto-detects Dockerfile and deploys

**Step 3:** Configure Environment Variables

In Railway dashboard, add variables as needed (see Configuration section below)

**Step 4:** Access Your Service
- Railway provides a public URL
- MCP endpoint: `https://your-service.railway.app/mcp`
- Health check: `https://your-service.railway.app/health`

#### 4.4: Other Cloud Platforms

The HTTP server can be deployed to any platform that supports:
- Docker containers
- Python applications
- Port binding via `PORT` environment variable

**Supported Platforms:**
- **Google Cloud Run** - Serverless container deployment
- **AWS ECS/Fargate** - Container orchestration
- **Azure Container Instances** - Container deployment
- **DigitalOcean App Platform** - PaaS deployment
- **Heroku** - Dyno-based deployment

**Deployment Pattern:**
1. Use the provided `Dockerfile`
2. Set `PORT` environment variable (if not auto-set by platform)
3. Configure health check to `GET /health`
4. Deploy and access at `https://your-domain.com/mcp`

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
