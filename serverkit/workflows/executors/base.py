from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serverkit.core.server import Server
    from serverkit.workflows.workflow import Workflow


class WorkflowExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        workflow: Workflow,
        server: Server,
        *,
        dry_run: bool = False,
    ) -> dict:
        pass
