"""Main workflow orchestrator using LangGraph."""

from typing import Literal
from langgraph.graph import StateGraph, END

from utils.state import AgentState, create_initial_state
from agents.refiner import refine_prompt
from agents.coder import generate_code, save_code
from agents.reviewer import review_code
from agents.tester import run_tests
from utils.flake8_checker import run_flake8


# Node functions for the graph

def refiner_node(state: AgentState) -> dict:
    """Refiner agent node - clarifies the user prompt."""
    refined = refine_prompt(state)
    history = state["refinement_history"] + [refined]
    return {
        "refined_prompt": refined,
        "refinement_history": history
    }


def coder_node(state: AgentState) -> dict:
    """Coder agent node - generates code."""
    # Increment attempt counter
    attempt = state["current_attempt"] + 1
    
    # Update problem description from confirmed refined prompt
    problem_desc = state["problem_description"]
    if not problem_desc and state["refined_prompt"]:
        problem_desc = state["refined_prompt"]
    
    # Generate code
    updated_state = {
        **state,
        "problem_description": problem_desc,
        "current_attempt": attempt
    }
    code = generate_code(updated_state)
    
    # Save code to file
    save_code(code, state["code_file_path"])
    
    return {
        "generated_code": code,
        "current_attempt": attempt,
        "problem_description": problem_desc,
        "workflow_status": "in_progress",
        "reviewer_status": None,
        "tester_status": None,
        "flake8_status": None
    }


def reviewer_node(state: AgentState) -> dict:
    """Reviewer agent node - reviews code."""
    result = review_code(state)
    
    updates = {
        "reviewer_status": result["status"],
        "reviewer_feedback": result["feedback"]
    }
    
    # If rejected, add to feedback history
    if result["status"] == "rejected":
        feedback_entry = {
            "source": "Reviewer",
            "message": result["feedback"],
            "attempt": state["current_attempt"]
        }
        updates["feedback_history"] = state["feedback_history"] + [feedback_entry]
    
    return updates


def tester_node(state: AgentState) -> dict:
    """Tester agent node - runs tests."""
    result = run_tests(state)
    
    updates = {
        "tester_status": result["status"],
        "tester_results": result["results"]
    }
    
    # If failed, add to feedback history
    if result["status"] == "fail":
        feedback_entry = {
            "source": "Tester",
            "message": f"Tests failed:\n{result['results']}",
            "attempt": state["current_attempt"]
        }
        updates["feedback_history"] = state["feedback_history"] + [feedback_entry]
    
    return updates


def flake8_node(state: AgentState) -> dict:
    """Flake8 linter node - checks code quality (INFORMATIONAL ONLY)."""
    result = run_flake8(state["generated_code"])
    
    # Check if there are issues
    has_issues = result.get("issues") and len(result["issues"]) > 0
    
    if has_issues:
        # Report issues found but mark as "clean" (don't block)
        updates = {
            "flake8_status": "issues_found",  # Informational status
            "flake8_report": result["issues"]
        }
    else:
        # No issues found
        updates = {
            "flake8_status": "clean",
            "flake8_report": []
        }
    
    # Don't add to feedback history - issues are informational only
    # This prevents looping back to coder
    
    return updates


def success_node(state: AgentState) -> dict:
    """Success node - marks workflow as complete."""
    return {
        "workflow_status": "success",
        "final_result": state["generated_code"]
    }


def failure_node(state: AgentState) -> dict:
    """Failure node - marks workflow as failed after max attempts."""
    return {
        "workflow_status": "failed"
    }


# Routing functions

def route_after_reviewer(state: AgentState) -> Literal["tester", "coder", "failure"]:
    """Route based on reviewer decision."""
    if state["reviewer_status"] == "approved":
        return "tester"
    elif state["current_attempt"] >= state["max_attempts"]:
        return "failure"
    else:
        return "coder"


def route_after_tester(state: AgentState) -> Literal["flake8", "coder", "failure"]:
    """Route based on tester results."""
    if state["tester_status"] == "pass":
        return "flake8"
    elif state["current_attempt"] >= state["max_attempts"]:
        return "failure"
    else:
        return "coder"


def route_after_flake8(state: AgentState) -> Literal["success"]:
    """Route after flake8 - ALWAYS proceed to success (informational only)."""
    # Flake8 reports issues but never blocks the workflow
    return "success"


def build_workflow() -> StateGraph:
    """Build and return the workflow graph (without refiner - handled by GUI)."""
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("flake8", flake8_node)
    workflow.add_node("success", success_node)
    workflow.add_node("failure", failure_node)
    
    # Set entry point
    workflow.set_entry_point("coder")
    
    # Add edges
    workflow.add_edge("coder", "reviewer")
    
    # Conditional edges
    workflow.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {
            "tester": "tester",
            "coder": "coder",
            "failure": "failure"
        }
    )
    
    workflow.add_conditional_edges(
        "tester",
        route_after_tester,
        {
            "flake8": "flake8",
            "coder": "coder",
            "failure": "failure"
        }
    )
    
    # Flake8 always goes to success (informational only)
    workflow.add_edge("flake8", "success")
    
    # End nodes
    workflow.add_edge("success", END)
    workflow.add_edge("failure", END)
    
    return workflow.compile()


# For testing without GUI
if __name__ == "__main__":
    from utils.state import create_initial_state
    
    # Test with a simple problem
    state = create_initial_state("create a function that adds two numbers")
    state["prompt_confirmed"] = True
    state["problem_description"] = "Create a Python function called 'add' that takes two numbers as parameters and returns their sum. Handle edge cases where inputs might not be numbers."
    state["workflow_status"] = "in_progress"
    
    # Build and run workflow
    app = build_workflow()
    
    print("Starting workflow...")
    print("=" * 50)
    
    final_state = app.invoke(state)
    
    print("\n" + "=" * 50)
    print(f"Final Status: {final_state['workflow_status']}")
    print(f"Attempts: {final_state['current_attempt']}")
    
    if final_state["workflow_status"] == "success":
        print("\nGenerated Code:")
        print(final_state["final_result"])
