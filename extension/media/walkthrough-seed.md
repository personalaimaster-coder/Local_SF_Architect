# Download model + seed

The engine uses a small local embedding model (~130 MB, downloaded once) and a
curated knowledge base of Salesforce governor limits and architecture patterns.

This step runs:

```
sf-architect doctor --download   # one-time model download
sf-architect seed                # build local databases
```

After this, the engine works fully offline.
