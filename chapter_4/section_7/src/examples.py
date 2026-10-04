"""Examples demonstrating the AI Agent framework.

This module provides comprehensive examples of using the agent framework with
various design patterns.
"""

from src.agent import (
    AgentBuilder,
    AgentNode,
    CategorizableToolBox,
    ChainOfThoughtStrategy,
    ConversationalMemory,
    Edge,
    EdgeType,
    ParallelGraphMediator,
    ReActStrategy,
    SimpleGraphMediator,
    TreeOfThoughtStrategy,
    WebSearchTool,
    WriteDraftTool,
    create_agent_from_config,
    create_default_controller,
)
from src.agent.memory import MemoryCaretaker
from src.client.llm_client import AnthropicModel
from src.logger import make_logger

logger = make_logger(__name__)


def example_1_basic_agent():
    """Example 1: Basic agent with Chain-of-Thought strategy."""
    logger.info("\n=== Example 1: Basic Agent with Chain-of-Thought ===\n")

    # Create components
    strategy = ChainOfThoughtStrategy(model=AnthropicModel.CLAUDE_HAIKU_4_5, max_steps=5)

    toolbox = CategorizableToolBox()
    toolbox.add_to_category("writing", WriteDraftTool())
    toolbox.add_to_category("search", WebSearchTool())

    # Build agent using Builder pattern
    agent = (
        AgentBuilder()
        .with_strategy(strategy)
        .with_toolbox(toolbox)
        .with_memory(ConversationalMemory(max_turns=20))
        .with_controller(create_default_controller(max_steps=10, max_cost=5.0))
        .with_agent_type("configurable")
        .with_config(enable_logging=True, max_iterations=10)
        .build()
    )

    # Execute agent
    goal = "Write a haiku about the changing seasons"
    result = agent.execute(goal)

    logger.info(f"Goal: {goal}")
    logger.info(f"Result:\n{result}")

    return result


def example_2_react_agent():
    """Example 2: Agent with ReAct strategy."""
    logger.info("\n=== Example 2: Agent with ReAct Strategy ===\n")

    # Build agent using fluent interface
    agent = (
        AgentBuilder()
        .with_strategy(
            {
                "type": "react",
                "model": AnthropicModel.CLAUDE_HAIKU_4_5,
                "max_iterations": 8,
            }
        )
        .with_toolbox(
            {
                "categorized": True,
                "tools": [
                    {"type": "write_draft", "category": "writing"},
                    {"type": "web_search", "category": "search"},
                ],
            }
        )
        .with_memory({"type": "conversational", "max_turns": 30})
        .with_controller(
            {
                "handlers": {
                    "max_steps": 20,
                    "max_cost": 8.0,
                    "max_calls_per_tool": 5,
                    "enable_dangerous_action_filter": True,
                    "enable_loop_detection": True,
                }
            }
        )
        .with_agent_type("configurable")
        .with_config(enable_logging=True)
        .build()
    )

    goal = "Search for information about the Eiffel Tower, then write a short poem inspired by what you learned"
    result = agent.execute(goal)

    logger.info(f"Goal: {goal}")
    logger.info(f"Result:\n{result}")

    return result


def example_3_multi_strategy_agent():
    """Example 3: Agent that can switch between strategies."""
    logger.info("\n=== Example 3: Multi-Strategy Agent ===\n")

    # Create multiple strategies
    strategies = {
        "cot": ChainOfThoughtStrategy(model=AnthropicModel.CLAUDE_HAIKU_4_5, max_steps=5),
        "react": ReActStrategy(model=AnthropicModel.CLAUDE_HAIKU_4_5, max_iterations=8),
        "tot": TreeOfThoughtStrategy(
            model=AnthropicModel.CLAUDE_HAIKU_4_5,
            max_depth=2,
            branch_factor=2,
        ),
    }

    toolbox = CategorizableToolBox()
    toolbox.add_to_category("writing", WriteDraftTool())

    agent = (
        AgentBuilder()
        .with_toolbox(toolbox)
        .with_memory(ConversationalMemory(max_turns=20))
        .with_agent_type("multi_strategy")
        .with_config(strategies=strategies, default_strategy="cot")
        .build()
    )

    # Use with default strategy (CoT)
    result1 = agent.execute("Write a limerick about a programmer")
    logger.info(f"Strategy: {agent.get_current_strategy()}")
    logger.info(f"Result:\n{result1}\n")

    # Switch to ReAct strategy
    agent.switch_strategy("react")
    result2 = agent.execute("Write a motivational quote about learning")
    logger.info(f"Strategy: {agent.get_current_strategy()}")
    logger.info(f"Result:\n{result2}")

    return result1, result2


def example_4_config_based_agent():
    """Example 4: Create agent from configuration dictionary."""
    logger.info("\n=== Example 4: Config-Based Agent Creation ===\n")

    config = {
        "type": "configurable",
        "strategy": {
            "type": "react",
            "model": AnthropicModel.CLAUDE_HAIKU_4_5,
            "max_iterations": 10,
        },
        "toolbox": {
            "categorized": True,
            "tools": [
                {"type": "write_draft", "category": "writing"},
                {"type": "web_search", "category": "information"},
            ],
        },
        "memory": {
            "type": "conversational",
            "max_turns": 50,
        },
        "controller": {
            "handlers": {
                "max_steps": 30,
                "max_cost": 10.0,
                "max_calls_per_tool": 8,
                "enable_dangerous_action_filter": True,
                "enable_loop_detection": True,
                "loop_window_size": 5,
                "loop_threshold": 3,
            }
        },
        "enable_logging": True,
        "max_iterations": 30,
    }

    # Create agent from config using Factory pattern
    agent = create_agent_from_config(config)

    goal = "Write a short story opening about a mysterious door"
    result = agent.execute(goal)

    logger.info(f"Goal: {goal}")
    logger.info(f"Result:\n{result}")

    return result


def example_5_graph_mediator():
    """Example 5: Multi-agent coordination using Mediator pattern."""
    logger.info("\n=== Example 5: Multi-Agent Graph with Mediator ===\n")

    # Create multiple specialized agents
    writing_agent = (
        AgentBuilder()
        .with_strategy(ChainOfThoughtStrategy(max_steps=10))
        .with_toolbox(
            {
                "tools": [{"type": "write_draft"}],
            }
        )
        .with_memory(ConversationalMemory(max_turns=10))
        .build()
    )

    search_agent = (
        AgentBuilder()
        .with_strategy(ReActStrategy(max_iterations=10))
        .with_toolbox(
            {
                "tools": [{"type": "web_search"}],
            }
        )
        .with_memory(ConversationalMemory(max_turns=10))
        .build()
    )

    # Create mediator
    mediator = SimpleGraphMediator()

    # Add agent nodes
    writing_node = AgentNode("writing_agent", writing_agent)
    search_node = AgentNode("search_agent", search_agent)

    mediator.add_node(writing_node)
    mediator.add_node(search_node)

    # Add edges (connections)
    mediator.add_edge(
        Edge(
            source_id="writing_agent",
            target_id="search_agent",
            edge_type=EdgeType.SEQUENTIAL,
        )
    )

    # Execute graph
    result = mediator.execute_graph(
        start_node_id="writing_agent",
        input_data="Write a creative tagline for a coffee shop",
    )

    logger.info("Graph Execution Results:")
    logger.info(f"Success: {result.success}")
    logger.info(f"Final Output:\n{result.final_output}")
    logger.info("\nExecution Log:")
    for log_entry in result.execution_log:
        logger.info(f"  Node: {log_entry.node_id}, Success: {log_entry.success}")

    return result


def example_6_parallel_execution():
    """Example 6: Parallel agent execution using ParallelGraphMediator."""
    logger.info("\n=== Example 6: Parallel Agent Execution ===\n")

    # Create agents for parallel execution
    agent1 = (
        AgentBuilder()
        .with_strategy(ChainOfThoughtStrategy(max_steps=10))
        .with_toolbox({"tools": [{"type": "write_draft"}]})
        .with_memory(ConversationalMemory(max_turns=10))
        .build()
    )

    agent2 = (
        AgentBuilder()
        .with_strategy(ReActStrategy(max_iterations=10))
        .with_toolbox({"tools": [{"type": "web_search"}]})
        .with_memory(ConversationalMemory(max_turns=10))
        .build()
    )

    # Create parallel mediator
    mediator = ParallelGraphMediator()

    # Add nodes
    node1 = AgentNode("agent1", agent1)
    node2 = AgentNode("agent2", agent2)
    mediator.add_node(node1)
    mediator.add_node(node2)

    # Create parallel edges
    mediator.add_edge(
        Edge(
            source_id="agent1",
            target_id="agent2",
            edge_type=EdgeType.PARALLEL,
        )
    )

    # Execute in parallel
    result = mediator.execute_graph(
        start_node_id="agent1",
        input_data="Write a short description of a sunset",
    )

    logger.info("Parallel Execution Results:")
    logger.info(f"Success: {result.success}")
    logger.info("\nExecution Log:")
    for log_entry in result.execution_log:
        parallel_flag = "PARALLEL" if log_entry.parallel else "SEQUENTIAL"
        logger.info(f"  [{parallel_flag}] Node: {log_entry.node_id}")

    return result


def example_7_memory_snapshots():
    """Example 7: Memory snapshots with Memento pattern."""
    logger.info("\n=== Example 7: Memory Snapshots (Memento Pattern) ===\n")
    logger.info("This example demonstrates saving and restoring agent memory state.\n")

    # Create agent with memory
    memory = ConversationalMemory(max_turns=10)

    agent = (
        AgentBuilder()
        .with_strategy(ChainOfThoughtStrategy(max_steps=10))
        .with_toolbox({"tools": [{"type": "write_draft"}]})
        .with_memory(memory)
        .build()
    )

    # Create memory caretaker
    caretaker = MemoryCaretaker()

    # Execute first task
    logger.info("Step 1: Execute first task...")
    result1 = agent.execute("Write a one-line joke about cats")
    logger.info(f"Task 1 result:\n{result1}")
    logger.info(f"Memory turns after task 1: {memory.get_context()['num_turns']}")

    # Save snapshot
    logger.info("\nStep 2: Saving memory snapshot (checkpoint)...")
    snapshot_id = caretaker.save(memory)
    logger.info(f"Snapshot saved with ID: {snapshot_id}")

    # Execute more tasks
    logger.info("\nStep 3: Execute additional tasks...")
    result2 = agent.execute("Write a pun about programming")
    logger.info(f"Task 2 result:\n{result2}")
    logger.info(f"Memory turns after task 2: {memory.get_context()['num_turns']}")

    result3 = agent.execute("Write a riddle about time")
    logger.info(f"Task 3 result:\n{result3}")
    logger.info(f"Memory turns after task 3: {memory.get_context()['num_turns']}")

    # Restore from snapshot
    logger.info("\nStep 4: Restoring memory to checkpoint...")
    logger.info(f"Memory turns BEFORE restore: {memory.get_context()['num_turns']}")
    caretaker.restore(memory, snapshot_id)
    logger.info(f"Memory turns AFTER restore: {memory.get_context()['num_turns']}")
    logger.info("Memory successfully restored to state after task 1 (tasks 2 and 3 are forgotten)!")

    return {"snapshot_id": snapshot_id, "restored": True}


def example_8_execution_control():
    """Example 8: Execution control with Chain of Responsibility."""
    logger.info("\n=== Example 8: Execution Control (Chain of Responsibility) ===\n")

    # Create agent with strict limits
    controller = create_default_controller(
        max_steps=10,
        max_cost=0.5,
        max_calls_per_tool=2,
    )

    agent = (
        AgentBuilder()
        .with_strategy(ChainOfThoughtStrategy(max_steps=10))
        .with_toolbox({"tools": [{"type": "write_draft"}]})
        .with_memory(ConversationalMemory(max_turns=10))
        .with_controller(controller)
        .with_agent_type("configurable")
        .with_config(enable_logging=True)
        .build()
    )

    result = agent.execute("Write an epic poem with multiple stanzas about the ocean")
    logger.info(f"Result:\n{result}")
    return result
