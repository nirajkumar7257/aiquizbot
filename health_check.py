"""
Health Check Server for Render Deployment
Provides HTTP endpoint on port 8080 for Render health checks
"""

import asyncio
import logging
from aiohttp import web

async def health_check_handler(request):
    """
    Simple health check endpoint for Render
    Returns 200 OK to indicate the service is running
    """
    return web.Response(text="OK", status=200)

async def ready_check_handler(request):
    """
    Ready check endpoint for Render
    Can be extended to check database connectivity, etc.
    """
    return web.json_response({
        "status": "ready",
        "service": "aiquizbot"
    }, status=200)

async def start_health_check_server(port: int = 8080):
    """
    Start the health check web server
    
    Args:
        port: Port to run the server on (default: 8080)
    
    Returns:
        web.AppRunner instance that can be managed
    """
    try:
        app = web.Application()
        
        # Health check routes
        app.router.add_get("/", health_check_handler)
        app.router.add_get("/health", health_check_handler)
        app.router.add_get("/ready", ready_check_handler)
        
        # Create runner
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Create site
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        
        logging.info(f"✅ Health check server started on 0.0.0.0:{port}")
        logging.info(f"   Endpoints: / | /health | /ready")
        
        return runner
        
    except Exception as e:
        logging.error(f"❌ Failed to start health check server: {e}")
        raise

async def stop_health_check_server(runner: web.AppRunner):
    """
    Gracefully stop the health check server
    
    Args:
        runner: The web.AppRunner instance
    """
    try:
        await runner.cleanup()
        logging.info("✅ Health check server stopped")
    except Exception as e:
        logging.error(f"❌ Error stopping health check server: {e}")
