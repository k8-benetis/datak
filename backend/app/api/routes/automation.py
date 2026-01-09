import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services.automation import AutomationRule, automation_engine

router = APIRouter(prefix="/automation", tags=["Automation"])

class RuleCreate(BaseModel):
    name: str
    condition: str
    target_sensor_id: int
    target_value: float
    cooldown_s: int = 5

class RuleResponse(BaseModel):
    id: str
    name: str
    condition: str
    target_sensor_id: int
    target_value: float
    cooldown_s: int
    last_triggered: float

@router.get("/rules", response_model=list[RuleResponse])
async def get_rules(user: CurrentUser) -> list[RuleResponse]:
    """Get all automation rules."""
    return [
        RuleResponse(
            id=r.id,
            name=r.name,
            condition=r.condition,
            target_sensor_id=r.target_sensor_id,
            target_value=r.target_value,
            cooldown_s=r.cooldown_s,
            last_triggered=r.last_triggered
        )
        for r in automation_engine._rules.values()
    ]

@router.post("/rules", response_model=RuleResponse)
async def create_rule(rule: RuleCreate, user: CurrentUser) -> RuleResponse:
    """Create a new automation rule."""
    rule_id = str(uuid.uuid4())
    new_rule = AutomationRule(
        rule_id=rule_id,
        name=rule.name,
        condition=rule.condition,
        target_sensor_id=rule.target_sensor_id,
        target_value=rule.target_value,
        cooldown_s=rule.cooldown_s
    )
    automation_engine.add_rule(new_rule)

    return RuleResponse(
        id=new_rule.id,
        name=new_rule.name,
        condition=new_rule.condition,
        target_sensor_id=new_rule.target_sensor_id,
        target_value=new_rule.target_value,
        cooldown_s=new_rule.cooldown_s,
        last_triggered=new_rule.last_triggered
    )

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, user: CurrentUser) -> dict:
    """Delete an automation rule."""
    if rule_id in automation_engine._rules:
        del automation_engine._rules[rule_id]
        return {"message": "Rule deleted"}
    raise HTTPException(status_code=404, detail="Rule not found")
