"""Examples demonstrating the AI Agent framework.

This module provides comprehensive examples of using the agent framework with
various design patterns.
"""

from src.agent import (
    AgentBuilder,
    AgentNode,
    CalculatorTool,
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
    create_agent_from_config,
    create_default_controller,
)
from src.agent.memory import MemoryCaretaker
from src.client.llm_client import GeminiModel
from src.logger import make_logger

logger = make_logger(__name__)


def example_1_basic_agent():
    """Example 1: Basic agent with Chain-of-Thought strategy."""
    logger.info("\n=== Example 1: Basic Agent with Chain-of-Thought ===\n")

    # Create components
    strategy = ChainOfThoughtStrategy(model=GeminiModel.GEMINI_2_5_FLASH, max_steps=5)

    toolbox = CategorizableToolBox()
    toolbox.add_to_category("math", CalculatorTool())
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
    goal = "Calculate the sum of 15 and 27, then multiply the result by 3"
    result = agent.execute(goal)

    logger.info(f"Goal: {goal}")
    logger.info(f"Result: {result}")

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
                "model": GeminiModel.GEMINI_2_5_FLASH,
                "max_iterations": 8,
            }
        )
        .with_toolbox(
            {
                "categorized": True,
                "tools": [
                    {"type": "calculator", "category": "math"},
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

    goal = "Search for the capital of France, then calculate 100 divided by 5"
    result = agent.execute(goal)

    logger.info(f"Goal: {goal}")
    logger.info(f"Result: {result}")

    return result


def example_3_multi_strategy_agent():
    """Example 3: Agent that can switch between strategies."""
    logger.info("\n=== Example 3: Multi-Strategy Agent ===\n")

    # Create multiple strategies
    strategies = {
        "cot": ChainOfThoughtStrategy(model=GeminiModel.GEMINI_2_5_FLASH, max_steps=5),
        "react": ReActStrategy(model=GeminiModel.GEMINI_2_5_FLASH, max_iterations=8),
        "tot": TreeOfThoughtStrategy(
            model=GeminiModel.GEMINI_2_5_FLASH,
            max_depth=2,
            branch_factor=2,
        ),
    }

    toolbox = CategorizableToolBox()
    toolbox.add_to_category("math", CalculatorTool())

    agent = (
        AgentBuilder()
        .with_toolbox(toolbox)
        .with_agent_type("multi_strategy")
        .with_config(strategies=strategies, default_strategy="cot")
        .build()
    )

    # Use with default strategy (CoT)
    result1 = agent.execute("Calculate 25 times 4")
    logger.info(f"Strategy: {agent.get_current_strategy()}")
    logger.info(f"Result: {result1}\n")

    # Switch to ReAct strategy
    agent.switch_strategy("react")
    result2 = agent.execute("Calculate 100 minus 37")
    logger.info(f"Strategy: {agent.get_current_strategy()}")
    logger.info(f"Result: {result2}")

    return result1, result2


def example_4_config_based_agent():
    """Example 4: Create agent from configuration dictionary."""
    logger.info("\n=== Example 4: Config-Based Agent Creation ===\n")

    config = {
        "type": "configurable",
        "strategy": {
            "type": "react",
            "model": GeminiModel.GEMINI_2_5_FLASH,
            "max_iterations": 10,
        },
        "toolbox": {
            "categorized": True,
            "tools": [
                {"type": "calculator", "category": "math"},
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

    goal = "Calculate the product of 12 and 15"
    result = agent.execute(goal)

    logger.info(f"Goal: {goal}")
    logger.info(f"Result: {result}")

    return result


def example_5_graph_mediator():
    """Example 5: Multi-agent coordination using Mediator pattern."""
    logger.info("\n=== Example 5: Multi-Agent Graph with Mediator ===\n")

    # Create multiple specialized agents
    math_agent = (
        AgentBuilder()
        .with_strategy(ChainOfThoughtStrategy(max_steps=3))
        .with_toolbox(
            {
                "tools": [{"type": "calculator"}],
            }
        )
        .build()
    )

    search_agent = (
        AgentBuilder()
        .with_strategy(ReActStrategy(max_iterations=5))
        .with_toolbox(
            {
                "tools": [{"type": "web_search"}],
            }
        )
        .build()
    )

    # Create mediator
    mediator = SimpleGraphMediator()

    # Add agent nodes
    math_node = AgentNode("math_agent", math_agent)
    search_node = AgentNode("search_agent", search_agent)

    mediator.add_node(math_node)
    mediator.add_node(search_node)

    # Add edges (connections)
    mediator.add_edge(
        Edge(
            source_id="math_agent",
            target_id="search_agent",
            edge_type=EdgeType.SEQUENTIAL,
        )
    )

    # Execute graph
    result = mediator.execute_graph(
        start_node_id="math_agent",
        input_data="Calculate 50 plus 50",
    )

    logger.info("Graph Execution Results:")
    logger.info(f"Success: {result.success}")
    logger.info(f"Final Output: {result.final_output}")
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
        .with_strategy(ChainOfThoughtStrategy(max_steps=3))
        .with_toolbox({"tools": [{"type": "calculator"}]})
        .build()
    )

    agent2 = (
        AgentBuilder()
        .with_strategy(ReActStrategy(max_iterations=3))
        .with_toolbox({"tools": [{"type": "web_search"}]})
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
        input_data="Process this task",
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

    # Create agent with memory
    memory = ConversationalMemory(max_turns=10)

    agent = (
        AgentBuilder()
        .with_strategy(ChainOfThoughtStrategy(max_steps=3))
        .with_toolbox({"tools": [{"type": "calculator"}]})
        .with_memory(memory)
        .build()
    )

    # Create memory caretaker
    caretaker = MemoryCaretaker()

    # Execute first task
    agent.execute("Calculate 10 plus 5")

    # Save snapshot
    snapshot_id = caretaker.save(memory)
    logger.info(f"Saved memory snapshot: {snapshot_id}")

    # Execute more tasks
    agent.execute("Multiply 7 by 8")
    agent.execute("Divide 100 by 4")

    logger.info(f"\nCurrent memory turns: {memory.get_context()['num_turns']}")

    # Restore from snapshot
    caretaker.restore(memory, snapshot_id)
    logger.info(f"Restored memory turns: {memory.get_context()['num_turns']}")
    logger.info("Memory restored to earlier state!")

    return {"snapshot_id": snapshot_id, "restored": True}


def example_8_execution_control():
    """Example 8: Execution control with Chain of Responsibility."""
    logger.info("\n=== Example 8: Execution Control (Chain of Responsibility) ===\n")

    # Create agent with strict limits
    controller = create_default_controller(
        max_steps=3,  # Very low limit to trigger
        max_cost=0.5,
        max_calls_per_tool=2,
    )

    agent = (
        AgentBuilder()
        .with_strategy(ChainOfThoughtStrategy(max_steps=10))
        .with_toolbox({"tools": [{"type": "calculator"}]})
        .with_controller(controller)
        .with_agent_type("configurable")
        .with_config(enable_logging=True)
        .build()
    )

    # This should hit the step limit
    result = agent.execute("Calculate a complex multi-step problem")

    logger.info(f"Result: {result}")
    logger.info("\nExecution was limited by the controller!")

    return result
