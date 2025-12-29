"""Parallel graph mediator with support for parallel execution."""

from datetime import datetime

from src.agent.core.mediator import (
    EdgeType,
    ExecutionLogEntry,
    GraphExecutionResult,
    NodeResult,
)
from src.agent.extensions.mediators.simple import SimpleGraphMediator


class ParallelGraphMediator(SimpleGraphMediator):
    """Graph mediator with support for parallel execution."""

    def execute_graph(self, start_node_id: str, input_data: str | dict | list) -> GraphExecutionResult:
        if start_node_id not in self.nodes:
            return self._error_result(f"Start node '{start_node_id}' not found")

        self._visited: set[str] = set()
        self._results: dict[str, NodeResult] = {}

        final_result = self._execute_node_recursive(start_node_id, input_data)
        return GraphExecutionResult(
            success=final_result.success,
            results=self._results,
            final_output=final_result.output,
            execution_log=self.execution_log.copy(),
            message_log=self.message_log.copy(),
        )

    def _error_result(self, error: str) -> GraphExecutionResult:
        return GraphExecutionResult(
            success=False,
            results={},
            final_output=None,
            execution_log=[],
            message_log=[],
            error=error,
        )

    def _execute_node_recursive(self, node_id: str, data: str | dict | list) -> NodeResult:
        if node_id in self._visited:
            return self._results.get(node_id) or NodeResult(node_id=node_id, success=False, output=None, error="Cycle")

        self._visited.add(node_id)
        result = self.nodes[node_id].execute(data)
        self._results[node_id] = result
        self._log_execution(node_id, result, parallel=False)

        if result.success and node_id in self.edges:
            self._execute_successors(node_id, result.output or "")

        return result

    def _execute_successors(self, node_id: str, output: str | dict | list) -> None:
        edges = self.edges[node_id]
        parallel_nodes = [e.target_id for e in edges if e.edge_type == EdgeType.PARALLEL]
        sequential_nodes = [e.target_id for e in edges if e.edge_type != EdgeType.PARALLEL]

        self._execute_parallel_nodes(parallel_nodes, output)
        self._execute_sequential_nodes(sequential_nodes, output)

    def _execute_parallel_nodes(self, node_ids: list[str], data: str | dict | list) -> None:
        for pid in node_ids:
            if pid not in self._visited:
                self._visited.add(pid)
                result = self.nodes[pid].execute(data)
                self._results[pid] = result
                self._log_execution(pid, result, parallel=True)

    def _execute_sequential_nodes(self, node_ids: list[str], data: str | dict | list) -> None:
        for sid in node_ids:
            self._execute_node_recursive(sid, data)

    def _log_execution(self, node_id: str, result: NodeResult, parallel: bool) -> None:
        self.execution_log.append(
            ExecutionLogEntry(
                timestamp=datetime.now(),
                node_id=node_id,
                success=result.success,
                output=result.output,
                parallel=parallel,
            )
        )
