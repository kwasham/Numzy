from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReceiptStatus
from app.models.tables import Receipt


async def _commit_and_refresh(session: AsyncSession, instance: Receipt) -> Receipt:
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(instance)
    return instance


async def create_receipt_record(
    session: AsyncSession,
    *,
    owner_id: int,
    file_path: str,
    filename: str,
    status: ReceiptStatus = ReceiptStatus.PENDING,
    extraction_progress: int = 0,
    audit_progress: int = 0,
    extracted_data: Dict[str, Any] | None = None,
    audit_decision: Dict[str, Any] | None = None,
) -> Receipt:
    receipt = Receipt(
        owner_id=owner_id,
        file_path=file_path,
        filename=filename,
        status=status,
        extraction_progress=extraction_progress,
        audit_progress=audit_progress,
        extracted_data=extracted_data,
        audit_decision=audit_decision,
    )
    session.add(receipt)
    return await _commit_and_refresh(session, receipt)


async def list_receipts_for_user(
    session: AsyncSession,
    *,
    owner_id: int,
    limit: int = 200,
    offset: int = 0,
) -> Sequence[Receipt]:
    query = (
        select(Receipt)
        .where(Receipt.owner_id == owner_id)
        .order_by(Receipt.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def get_receipt_for_user(
    session: AsyncSession,
    *,
    owner_id: int,
    receipt_id: int,
) -> Receipt | None:
    query = select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == owner_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_receipt_by_id(
    session: AsyncSession,
    *,
    receipt_id: int,
) -> Receipt | None:
    result = await session.execute(select(Receipt).where(Receipt.id == receipt_id))
    return result.scalar_one_or_none()


async def update_receipt_record(
    session: AsyncSession,
    receipt: Receipt,
    **fields: Any,
) -> Receipt:
    if not fields:
        return receipt
    fields.setdefault("updated_at", datetime.utcnow())
    for key, value in fields.items():
        setattr(receipt, key, value)
    return await _commit_and_refresh(session, receipt)


async def delete_receipt_record(
    session: AsyncSession,
    receipt: Receipt,
) -> None:
    await session.delete(receipt)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def reset_receipt_for_reprocess(
    session: AsyncSession,
    receipt: Receipt,
) -> Receipt:
    receipt.status = ReceiptStatus.PENDING
    receipt.task_error = None
    receipt.task_retry_count = 0
    receipt.extraction_progress = 0
    receipt.audit_progress = 0
    receipt.task_started_at = None
    receipt.task_completed_at = None
    receipt.updated_at = datetime.utcnow()
    return await _commit_and_refresh(session, receipt)
