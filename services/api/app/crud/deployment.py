from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select
from app.models import Deployment, System
from fastapi import HTTPException
from uuid import UUID
from typing import List
from schemas.deployment_schemas import DeploymentWrite, DeploymentUpdate

async def get_deployment(db: AsyncSession, deployment_id: UUID) -> Deployment:
    """Get a single deployment by its ID."""
    statement = (
        select(Deployment)
        .where(Deployment.id == deployment_id)
    )
    result = await db.execute(statement)
    deployment = result.scalars().first()

    if not deployment:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

    return deployment


async def get_all_deployments(db: AsyncSession) -> List[Deployment]:
    """Get all deployments."""

    statement = select(Deployment)

    result = await db.execute(statement)
    deployments = result.scalars().all()

    if not deployments:
        raise HTTPException(status_code=404, detail="No deployments were found")

    return deployments


async def create_deployment(db: AsyncSession, system_id: UUID, deployment_in) -> Deployment:
    """Check the system exists."""
    statement = (
        select(System)
        .where(System.id == system_id)
    )
    result = await db.execute(statement)
    system = result.scalars().first()

    if not system:
        raise HTTPException(status_code=404, detail=f"System {system_id} not found")

    """Create a new deployment in the database."""
    deployment_data = deployment_in.model_dump()
    new_deployment = Deployment(
        **deployment_data,
        system_id=system_id,  # Set system_id explicitly
    )
    try:
        db.add(new_deployment)
        await db.commit()
        await db.refresh(new_deployment)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating deployment: {str(e)}")

    return new_deployment

async def update_deployment(db: AsyncSession, db_deployment: Deployment, deployment_in: DeploymentUpdate) -> Deployment:
    update_data = deployment_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_deployment, key, value)

    try:
        await db.commit()
        await db.refresh(db_deployment)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return db_deployment



async def delete_deployment(db: AsyncSession, db_deployment: Deployment):
    try:
        await db.delete(db_deployment)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error deleting deployment: {str(e)}")
