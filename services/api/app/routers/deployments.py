from fastapi import APIRouter, Depends, status, Query
from schemas.deployment_schemas import DeploymentRead, DeploymentWrite, DeploymentUpdate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.crud.deployment import get_all_deployments, get_deployment, create_deployment, update_deployment, delete_deployment
from pydantic import UUID4

router = APIRouter()

@router.get("/", response_model=List[DeploymentRead], summary="List Deployments", description="List deployments with optional filtering, pagination, and sorting")
async def read_deployments(db: AsyncSession = Depends(get_db)):

    deployments_data = await get_all_deployments(db)

    return [DeploymentRead(**{k: v for k, v in deployment.__dict__.items() if not k.startswith("_")}) for deployment in deployments_data]


@router.get("/{deployment_id}", summary="Get Deployment by ID", status_code=status.HTTP_200_OK, response_model=DeploymentRead)
async def get_a_deployment_by_id(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    db_deployment = await get_deployment(db, deployment_id=deployment_id)

    # Build a clean dictionary of attributes
    deployment_data = {k: v for k, v in db_deployment.__dict__.items() if not k.startswith("_")}

    return DeploymentRead(**deployment_data)


@router.post("/", summary="Create Deployment", status_code=status.HTTP_201_CREATED, response_model=DeploymentRead)
async def create_a_new_deployment(systemId: UUID4, deployment_in: DeploymentWrite, db: AsyncSession = Depends(get_db)):
    created_deployment_db = await create_deployment(db=db, system_id=systemId, deployment_in=deployment_in)

    # Build a clean dictionary of attributes
    deployment_data = {k: v for k, v in created_deployment_db.__dict__.items() if not k.startswith("_")}

    # Validate and return Pydantic model
    return DeploymentRead(**deployment_data)


@router.put("/{deployment_id}", summary="Update Deployment", status_code=status.HTTP_200_OK, response_model=DeploymentRead)
async def update_a_deployment(deployment_id: UUID, deployment_in: DeploymentUpdate, db: AsyncSession = Depends(get_db)):
    db_deployment_to_update = await get_deployment(db, deployment_id=deployment_id)

    updated_deployment_db = await update_deployment(
        db=db, db_deployment=db_deployment_to_update, deployment_in=deployment_in
    )

    deployment_data = {k: v for k, v in updated_deployment_db.__dict__.items() if not k.startswith("_")}

    # Validate and return Pydantic model
    return DeploymentRead(**deployment_data)


@router.delete("/{deployment_id}", summary="Delete Deployment", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db)):
    db_deployment_to_delete = await get_deployment(db, deployment_id=deployment_id)

    await delete_deployment(db=db, db_deployment=db_deployment_to_delete)

    return None
