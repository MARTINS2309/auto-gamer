import uuid

from fastapi import APIRouter, HTTPException

from ..models.db import AgentModel, RomModel, RunModel, SessionLocal
from ..models.schemas import AgentCreate, AgentResponse, AgentUpdate

router = APIRouter()


def _enrich_agent(agent: AgentModel, db) -> AgentModel:
    """Add game_name attribute to agent for response serialization."""
    game_name = None
    if agent.game_id:
        rom = db.query(RomModel).filter(RomModel.id == agent.game_id).first()
        if rom:
            game_name = rom.display_name
    agent.game_name = game_name  # type: ignore[attr-defined]
    return agent


@router.post("/agents", response_model=AgentResponse)
def create_agent(agent_in: AgentCreate):
    db = SessionLocal()
    try:
        # Check unique name
        existing = db.query(AgentModel).filter(AgentModel.name == agent_in.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Agent with name '{agent_in.name}' already exists")

        agent = AgentModel(
            id=str(uuid.uuid4()),
            name=agent_in.name,
            description=agent_in.description,
            algorithm=agent_in.algorithm.value,
            game_id=agent_in.game_id,
            hyperparams=agent_in.hyperparams.model_dump() if agent_in.hyperparams else None,
            observation_type=agent_in.observation_type.value,
            action_space=agent_in.action_space.value,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        _enrich_agent(agent, db)
        return agent
    finally:
        db.close()


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(sort_by: str = "best_reward", game_id: str | None = None):
    """List all agents, sorted by best_reward descending (for leaderboard)."""
    db = SessionLocal()
    try:
        query = db.query(AgentModel)
        if game_id:
            query = query.filter(AgentModel.game_id == game_id)
        if sort_by == "best_reward":
            query = query.order_by(AgentModel.best_reward.desc().nullslast())
        elif sort_by == "total_steps":
            query = query.order_by(AgentModel.total_steps.desc())
        elif sort_by == "created_at":
            query = query.order_by(AgentModel.created_at.desc())
        else:
            query = query.order_by(AgentModel.created_at.desc())
        agents = query.all()
        for agent in agents:
            _enrich_agent(agent, db)
        return agents
    finally:
        db.close()


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str):
    db = SessionLocal()
    try:
        agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        _enrich_agent(agent, db)
        return agent
    finally:
        db.close()


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, agent_update: AgentUpdate):
    db = SessionLocal()
    try:
        agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if agent_update.name is not None:
            # Check unique name (exclude self)
            existing = (
                db.query(AgentModel)
                .filter(AgentModel.name == agent_update.name, AgentModel.id != agent_id)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400, detail=f"Agent with name '{agent_update.name}' already exists"
                )
            agent.name = agent_update.name  # type: ignore[assignment]

        if agent_update.description is not None:
            agent.description = agent_update.description  # type: ignore[assignment]

        if agent_update.hyperparams is not None:
            agent.hyperparams = agent_update.hyperparams.model_dump()  # type: ignore[assignment]

        db.commit()
        db.refresh(agent)
        _enrich_agent(agent, db)
        return agent
    finally:
        db.close()


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: str):
    db = SessionLocal()
    try:
        agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Nullify agent_id on associated runs (don't delete the runs)
        db.query(RunModel).filter(RunModel.agent_id == agent_id).update(
            {RunModel.agent_id: None}
        )

        db.delete(agent)
        db.commit()
        return None
    finally:
        db.close()
