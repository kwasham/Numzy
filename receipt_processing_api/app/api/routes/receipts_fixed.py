# This is a temporary fix for the nl_rule_description issue
# Copy this to receipts.py after backing up the original

async def process_receipt_task(receipt_id: int, user_id: int) -> None:
    """Background task to extract and audit receipt."""
    async with get_db() as session:
        try:
            rec = await session.get(Receipt, receipt_id)
            if not rec:
                return
            rec.status = ReceiptStatus.PROCESSING
            await session.commit()
            # Load file data
            storage_inner = StorageService()
            file_bytes = storage_inner.get_full_path(rec.file_path).read_bytes()
            extraction_service = ExtractionService()
            details = await extraction_service.extract(file_bytes, rec.filename)
            # Run audit
            audit_service = AuditService(session)
            
            # FIXED: Don't try to access non-existent attributes
            # Just use default audit without NL rules for now
            decision = await audit_service.audit(details, user_id)
            
            # Update receipt record
            rec.extracted_data = details.model_dump()
            rec.audit_decision = decision.model_dump()
            rec.status = ReceiptStatus.COMPLETED
            await session.commit()
        except Exception as e:
            # Log the error but don't crash
            print(f"Error processing receipt {receipt_id}: {str(e)}")
            if rec:
                rec.status = ReceiptStatus.FAILED
                await session.commit()