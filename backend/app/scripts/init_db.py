"""Initialize database tables."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import init_db

async def main():
    print("Initializing database tables...")
    await init_db()
    print("Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(main())