"""Assembles nodes, edges, and checkpointer into the compiled StateGraph.

Single responsibility: build_graph() constructs the StateGraph[AgentState],
registers model / tools / finalize nodes using factories from nodes.py,
wires edges START->model, model->{tools|END}, tools->{model|finalize},
finalize->END using routing functions from routing.py, and compiles with
the injected checkpointer. Accepts an optional model argument so tests can
substitute a scripted fake without an Anthropic key. Only the model node
receives a tools-bound model; the finalizer node uses the unbound base model.

Governed by:
  §"Graph loop and termination contract" in 00-roadmap-and-contracts.md
  §"agent/app/graph.py" in 02-langgraph-agent.md
"""
