import asyncio
from app.core.database import get_db
from app.models.tables import Receipt
from sqlalchemy import select, func

async def check_db():
    async for session in get_db():
        try:
            # Count total receipts
            count_result = await session.execute(select(func.count(Receipt.id)))
            total = count_result.scalar()
            print(f'Total receipts in database: {total}')
            
            # Get latest receipts
            result = await session.execute(
                select(Receipt).order_by(Receipt.id.desc()).limit(5)
            )
            receipts = result.scalars().all()
            
            if receipts:
                print('\nLatest receipts:')
                for r in receipts:
                    print(f'ID: {r.id}, Status: {r.status}, Created: {r.created_at}')
                    if r.extracted_data:
                        print(f'  Extracted data present: Yes, Total: ${r.extracted_data.get("total", "N/A")}')
                    if r.audit_decision:
                        print(f'  Audit decision present: Yes, Needs audit: {r.audit_decision.get("needs_audit", "N/A")}')
            else:
                print('No receipts found in database')
        finally:
            await session.close()
        break

asyncio.run(check_db())
