import time

from langgraph.graph import END, START, StateGraph
from signalpost.agent.budget import BudgetManager
from signalpost.agent.nodes import AgentNodes
from signalpost.agent.state import AgentState
from signalpost.schemas.profile import CompanyProfile


def create_signalpost_graph(nodes: AgentNodes):
    """
    Constructs the LangGraph state machine with conditional routing and budget awareness.
    """
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("validate_input", nodes.validate_input)
    builder.add_node("fetch_registry", nodes.fetch_registry)
    builder.add_node("resolve_website", nodes.resolve_website)
    builder.add_node("crawl_site", nodes.crawl_site)
    builder.add_node("extract_facts", nodes.extract_facts)
    builder.add_node("verify_match", nodes.verify_match)
    builder.add_node("validate_facts", nodes.validate_facts)
    builder.add_node("diff_and_update", nodes.diff_and_update)
    builder.add_node("explain", nodes.explain)
    builder.add_node("persist_and_emit", nodes.persist_and_emit)

    # Edge: Start -> validate_input
    builder.add_edge(START, "validate_input")

    # Conditional edge: validate_input
    def route_after_validate(state: AgentState) -> str:
        if not state.get("is_valid_orgnr"):
            return "persist_and_emit"
        return "fetch_registry"

    builder.add_conditional_edges("validate_input", route_after_validate)

    # Conditional edge: fetch_registry
    def route_after_registry(state: AgentState) -> str:
        # Bankrupt, dissolved, not found, or early stop: skip web crawl
        if state.get("stop_early") or not state.get("found_in_registry"):
            return "validate_facts"
        return "resolve_website"

    builder.add_conditional_edges("fetch_registry", route_after_registry)

    # Conditional edge: resolve_website
    def route_after_resolve_website(state: AgentState) -> str:
        if not state.get("candidate_urls"):
            return "validate_facts"
        return "crawl_site"

    builder.add_conditional_edges("resolve_website", route_after_resolve_website)

    # Sequential edges for fact extraction and verification
    builder.add_edge("crawl_site", "extract_facts")
    builder.add_edge("extract_facts", "verify_match")
    builder.add_edge("verify_match", "validate_facts")
    builder.add_edge("validate_facts", "diff_and_update")
    builder.add_edge("diff_and_update", "explain")
    builder.add_edge("explain", "persist_and_emit")
    builder.add_edge("persist_and_emit", END)

    return builder.compile()


class SignalpostAgent:
    """
    High-level orchestrator interface to run the LangGraph Signalpost agent.
    """

    def __init__(self, budget_manager: BudgetManager | None = None):
        self.budget_manager = budget_manager or BudgetManager()
        self.nodes = AgentNodes(budget_manager=self.budget_manager)
        self.graph = create_signalpost_graph(self.nodes)

    async def run(self, org_number: str) -> CompanyProfile:
        """
        Executes the full pipeline for a 9-digit Norwegian organization number.
        Returns the verified, schema-compliant CompanyProfile.
        """
        initial_state: AgentState = {
            "org_number": org_number,
            "start_time": time.time(),
            "requests_used": 0,
            "cost_usd": 0.0,
            "facts": [],
            "rejected_facts": [],
            "warnings": [],
        }

        final_state = await self.graph.ainvoke(initial_state)
        profile = final_state.get("final_profile")

        if not profile:
            raise RuntimeError(f"Agent failed to emit final profile for orgnr {org_number}")

        return profile
