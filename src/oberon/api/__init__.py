"""API package — typed request/response contracts for the Rust control plane.

This is the Python-side pre-work for 008-rust-control-plane. It defines the
canonical Pydantic models that the Rust Axum API will mirror. The Rust side
deserializes incoming JSON into its own types, spawns the Python pipeline, and
serializes the response using these same contract shapes.

See: docs/api/gaps_vs_product_brief.md for the full gap analysis.
"""
