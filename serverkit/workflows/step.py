"""Abstract workflow step and concrete step types."""

from __future__ import annotations

from abc import ABC, abstractmethod


class WorkflowStep(ABC):
    """One node in a workflow pipeline."""

    @abstractmethod
    def execute(self, context: dict) -> dict:
        """Run this step and return updated context."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize step for workflow JSON."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> WorkflowStep:
        """Deserialize step from workflow JSON."""
