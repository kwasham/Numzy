# app/services/prompt_templates.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import PromptTemplate
from app.models.schemas import PromptTemplateCreate

class PromptTemplateRepository:
    async def create(self, db: AsyncSession, template: PromptTemplateCreate) -> PromptTemplate:
        """Create and persist a new PromptTemplate."""
        new_prompt = PromptTemplate(
            name=template.name,
            type=template.type,
            content=template.content,
            owner_id=template.owner_id,
            organisation_id=template.organisation_id,
        )
        db.add(new_prompt)
        await db.commit()
        await db.refresh(new_prompt)
        return new_prompt

    async def get(self, prompt_id: int, db: AsyncSession) -> Optional[PromptTemplate]:
        """Retrieve a PromptTemplate by ID."""
        return await db.get(PromptTemplate, prompt_id)

    # You could add list/update/delete methods here if needed.

# Export a singleton instance for easy import
prompt_template_repository = PromptTemplateRepository()
