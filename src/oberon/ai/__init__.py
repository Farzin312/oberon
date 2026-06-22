"""AI model adapters — foundation model integration for Oberon.

All AI models live behind the ModelAdapter protocol. No torch or model
imports leak into the pipeline core. The orchestrator imports from this
package only when --use-ai is set.
"""
