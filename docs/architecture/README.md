# Architecture

**Parent**: [README.md](../README.md)

**Children**: [SYSTEM_DESIGN](SYSTEM_DESIGN.md) · [DATA_FLOW](DATA_FLOW.md)

Oberon is a functional-core, imperative-shell system organized into four conceptual planes. See [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for the full architecture and [DATA_FLOW.md](DATA_FLOW.md) for the pipeline data flow.

## Quick reference

```bash
# View all subsystem boundaries
bounds list

# View a specific subsystem manifest
bounds describe <subsystem-name>

# Validate everything is consistent
bounds validate --quick

# Check for boundary violations before PR
bounds preflight --ci
```
