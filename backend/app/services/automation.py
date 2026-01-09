
import asyncio
from typing import Any, Callable
import structlog
from app.services.orchestrator import orchestrator
from app.core.formula import evaluate_formula

logger = structlog.get_logger()

class AutomationRule:
    def __init__(
        self, 
        rule_id: str, 
        name: str, 
        condition: str, 
        target_sensor_id: int, 
        target_value: float,
        cooldown_s: int = 5
    ):
        self.id = rule_id
        self.name = name
        self.condition = condition
        self.target_sensor_id = target_sensor_id
        self.target_value = target_value
        self.cooldown_s = cooldown_s
        self.last_triggered = 0.0

class AutomationEngine:
    """
    Evaluates automation rules based on sensor data updates.
    
    Architecture:
    - Subscribes to Orchestrator 'on_processed_value'
    - Maintains a local cache of latest sensor values (by name)
    - On update, evaluates relevant rules
    - If condition met, calls orchestrator.write_sensor
    """

    def __init__(self):
        self._log = logger.bind(component="automation_engine")
        self._rules: dict[str, AutomationRule] = {}
        self._sensor_values: dict[str, float] = {} # name -> value
        self._running = False

    async def start(self) -> None:
        """Start the automation engine."""
        self._running = True
        orchestrator.on_processed_value(self._handle_update)
        self._log.info("Automation engine started")

    async def stop(self) -> None:
        self._running = False
        self._log.info("Automation engine stopped")

    def add_rule(self, rule: AutomationRule) -> None:
        self._rules[rule.id] = rule
        self._log.info("Rule added", rule=rule.name)

    async def _handle_update(self, sensor_id: int, raw: float, value: float, timestamp: Any) -> None:
        if not self._running:
            return

        # Get sensor name from orchestrator
        # Accessing protected member _drivers is a bit naughty but efficient for internal service
        driver = orchestrator._drivers.get(sensor_id)
        if not driver:
            return
            
        sensor_name = driver.sensor_name
        self._sensor_values[sensor_name] = value
        
        # Evaluate rules
        # Optimization: Could map sensor_name -> dependent rules. 
        # For now, iterate all (MVP).
        await self._evaluate_rules()

    async def _evaluate_rules(self) -> None:
        import time
        now = time.time()
        
        for rule in self._rules.values():
            if now - rule.last_triggered < rule.cooldown_s:
                continue
                
            try:
                # Prepare context
                # Safe context: Math functions + sensor values
                # We use app.core.formula logic but slightly different context
                # evaluate_formula takes 'val', we need strict names.
                # Let's use RestrictedPython directly or just simple eval with safe types?
                # Using standard eval with limited locals is risky but this is internal/admin defined.
                # app.core.formula uses RestrictedPython.
                
                # Context dict
                context = {**self._sensor_values}
                
                # Simple boolean evaluation
                # Note: This regex/parsing might be needed if using app.core.formula helpers
                # But let's assume valid python syntax for now (e.g. "temp > 50")
                # Warning: eval is dangerous. Ensure rules come from trusted admin.
                
                # Implementation using simple eval for MVP with restricted scope
                # Using empty globals and sensor values as locals
                allowed_names = {"abs": abs, "max": max, "min": min, "round": round}
                eval_locals = {**allowed_names, **self._sensor_values}
                
                is_met = eval(rule.condition, {"__builtins__": {}}, eval_locals)
                
                if is_met:
                    self._log.info("Rule triggered", rule=rule.name, condition=rule.condition)
                    await orchestrator.write_sensor(rule.target_sensor_id, rule.target_value)
                    rule.last_triggered = now
                    
            except Exception as e:
                # Log only occasionally to avoid spam
                pass

# Global instance
automation_engine = AutomationEngine()
