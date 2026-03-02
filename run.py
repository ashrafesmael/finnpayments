#!/usr/bin/env python3
"""
FinnPayments - Invoice Processing & Accounting Entries
"""
import uvicorn
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/finnpayments.log', mode='a')
    ]
)

logger = logging.getLogger("FinnPayments")

def main():
    host = os.getenv("FINNPAYMENTS_HOST", "0.0.0.0")
    port = int(os.getenv("FINNPAYMENTS_PORT", "8001"))
    
    logger.info("=" * 50)
    logger.info("FinnPayments - Invoice Processing & Accounting")
    logger.info(f"Starting server on {host}:{port}")
    logger.info("=" * 50)
    
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
