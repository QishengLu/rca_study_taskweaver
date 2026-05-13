"""TaskWeaver eval agent — wraps legacy agent_runner.py.

Note: TaskWeaver is code-generation based (Planner + CodeInterpreter), so the
trajectory has Post objects rather than tool_calls. The legacy agent_runner.py
already does the Post→OpenAI-flat conversion; we just wrap with v3 Trajectory.
"""
from __future__ import annotations

from pathlib import Path

from sota_rca.legacy_agent import LegacySubprocessAgent, LegacyAgentConfig

_FW_DIR = Path(__file__).resolve().parent.parent.parent.parent  # frameworks/taskweaver


class TaskWeaverEvalAgent(LegacySubprocessAgent):
    @staticmethod
    def name() -> str:
        return "taskweaver"

    @classmethod
    def _default_config(cls) -> LegacyAgentConfig:
        return LegacyAgentConfig(
            framework_name="taskweaver",
            framework_dir=_FW_DIR,
            cmd=["uv", "run", "python", "agent_runner.py"],
            prompt_yaml=_FW_DIR / "src" / "taskweaver_rca" / "prompts" / "agents" / "langgraph" / "rca.yaml",
            timeout=2400,  # TaskWeaver tends to be slow (kernel + code gen)
            multi_agent=False,
        )
