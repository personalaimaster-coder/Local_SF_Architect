# Download model + seed

The engine uses small local embedding and reranker models (~210 MB total,
downloaded once) and a curated knowledge base of Salesforce governor limits and
architecture patterns (78 patterns across the Well-Architected pillars).

This step runs:

```
sf-architect doctor --download   # one-time model download
sf-architect seed                # build local databases
```

After this, the engine works fully offline.
