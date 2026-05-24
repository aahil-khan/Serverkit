from serverkit.workflows.executors.parallel import ParallelExecutor
from serverkit.workflows.executors.sequential import SequentialExecutor

EXECUTORS = {
    "sequential": SequentialExecutor,
    "parallel": ParallelExecutor,
}


def get_executor(name: str) -> SequentialExecutor:
    cls = EXECUTORS.get(name, SequentialExecutor)
    return cls()
