# Ruflo v3.0 — Full Capabilities Reference

> **Ruflo is the AI intelligence layer.** Viking finds project docs. Ruflo makes the AI smarter.

## Viking vs Ruflo

| | Viking (OpenViking MCP) | Ruflo (claude-flow MCP) |
|---|---|---|
| **Purpose** | Search project documentation | AI self-learning + agent orchestration |
| **Data** | 93+ indexed docs, 727 embeddings | Patterns, trajectories, task routing |
| **Embeddings** | Model2Vec 256-dim | all-MiniLM-L6-v2 384-dim + Poincaré hyperbolic |
| **Search** | Semantic over docs | HNSW vector search over learned patterns |
| **Who uses it** | Claude (to find answers) | Claude (to learn from experience) |
| **Persistence** | Static index (rebuild on change) | Dynamic (grows every session) |

**Use both:** Viking for "what does the project say about X?" — Ruflo for "what patterns have I learned about X?"

---

## Architecture

```
Ruflo v3.0
├── Memory (sql.js + HNSW)          ← Key-value + vector search
│   ├── Namespaces: pattern, default, locanext, architecture, system
│   ├── 100% embedding coverage
│   └── Semantic search with similarity threshold
├── Intelligence (RuVector)          ← Self-learning layer
│   ├── SONA: Trajectory-based reinforcement learning
│   ├── MoE: 8-expert mixture (coder/tester/reviewer/architect/security/perf/researcher/coordinator)
│   ├── EWC++: Prevents catastrophic forgetting during learning
│   ├── Flash Attention: Fast similarity computation
│   ├── LoRA: Low-rank adaptation for fine-tuning
│   └── HNSW: 150x-12,500x faster vector search
├── Embeddings (ONNX)               ← Vector generation
│   ├── Model: all-MiniLM-L6-v2 (384-dim)
│   ├── Hyperbolic: Poincaré ball embeddings (hierarchical data)
│   ├── Compare: cosine, euclidean, poincaré distance
│   └── Neural substrate: drift detection, consolidation
├── Agents                           ← Spawnable workers
│   ├── Pool management (scale, drain, fill)
│   ├── Health monitoring
│   └── Domain-based filtering
├── Swarm                            ← Multi-agent coordination
│   ├── Topology: hierarchical, mesh, ring
│   ├── Hive-mind: shared memory across agents
│   └── Consensus protocols
├── Neural                           ← Model training
│   ├── Types: MoE, transformer, classifier, embedding
│   ├── Compression: quantize, prune, distill
│   └── Pattern storage and search
└── Hooks                            ← Event-driven learning
    ├── pre/post-task, pre/post-edit, pre/post-command
    ├── Session start/end/restore
    └── Worker dispatch/detect/cancel
```

---

## 175+ Tools by Category

### 1. Memory (HNSW Vector Store)

| Tool | What it does |
|------|-------------|
| `memory_store` | Store key-value with auto-embedding (upsert supported) |
| `memory_retrieve` | Get by key |
| `memory_search` | **Semantic vector search** (HNSW, 150x faster) |
| `memory_list` | List entries, filter by namespace |
| `memory_delete` | Remove entry |
| `memory_stats` | Index status, embedding coverage |
| `memory_migrate` | Migrate from legacy JSON to sql.js |

**Namespaces:** Organize memories by topic — `pattern`, `default`, `locanext`, `architecture`, `system`, or custom.

### 2. Intelligence (RuVector — Self-Learning)

| Tool | What it does |
|------|-------------|
| `hooks_intelligence` | System status, enable HNSW/MoE/SONA |
| `hooks_intelligence_stats` | Detailed metrics across all subsystems |
| `hooks_intelligence_pattern-store` | Store a learned pattern (HNSW-indexed) |
| `hooks_intelligence_pattern-search` | Search patterns by semantic similarity |
| `hooks_intelligence_trajectory-start` | Begin tracking a task (reinforcement learning) |
| `hooks_intelligence_trajectory-step` | Record action + quality score in trajectory |
| `hooks_intelligence_trajectory-end` | End trajectory, trigger SONA learning |
| `hooks_intelligence_learn` | Force learning cycle with EWC++ consolidation |
| `hooks_intelligence_attention` | Attention-weighted search (flash/moe/hyperbolic) |
| `hooks_intelligence-reset` | Reset learning state |

**How SONA learning works:**
1. `trajectory-start` → begin tracking a task
2. `trajectory-step` (×N) → record each action + quality (0-1)
3. `trajectory-end` → mark success/failure, trigger learning
4. Ruflo extracts patterns from successful trajectories
5. EWC++ prevents forgetting old patterns when learning new ones

### 3. Embeddings (ONNX + Hyperbolic)

| Tool | What it does |
|------|-------------|
| `embeddings_init` | Initialize ONNX model (MiniLM or mpnet) |
| `embeddings_generate` | Generate embedding for text (Euclidean or Poincaré) |
| `embeddings_search` | Semantic search across stored embeddings |
| `embeddings_compare` | Compare two texts (cosine/euclidean/poincaré) |
| `embeddings_status` | System status |
| `embeddings_hyperbolic` | Convert, distance, midpoint in Poincaré ball |
| `embeddings_neural` | Neural substrate: drift detection, consolidation |

**Hyperbolic embeddings:** Better for hierarchical data (code structures, file trees, category hierarchies). Standard cosine for flat comparisons.

### 4. Agents + Swarm

| Tool | What it does |
|------|-------------|
| `agent_spawn` | Create agent with model routing (haiku/sonnet/opus) |
| `agent_list/status/health` | Monitor agents |
| `agent_pool` | Scale, drain, fill agent pools |
| `agent_terminate` | Kill agent |
| `swarm_init` | Initialize multi-agent swarm (topology: hierarchical/mesh/ring) |
| `swarm_status/health` | Monitor swarm |
| `swarm_shutdown` | Graceful or forced shutdown |
| `hive-mind_init/join/leave` | Shared consciousness across agents |
| `hive-mind_memory` | Get/set/delete shared memory |
| `hive-mind_broadcast` | Send message to all hive members |
| `hive-mind_consensus` | Distributed decision-making |

### 5. Hooks (Event-Driven)

| Tool | What it does |
|------|-------------|
| `hooks_pre-task/post-task` | Before/after task execution |
| `hooks_pre-edit/post-edit` | Before/after file edits |
| `hooks_pre-command/post-command` | Before/after shell commands |
| `hooks_session-start/end/restore` | Session lifecycle |
| `hooks_route` | Route to appropriate handler |
| `hooks_model-route/outcome/stats` | Model selection intelligence |
| `hooks_worker-*` | Background worker management |
| `hooks_notify` | Send notifications |

### 6. Neural (Model Training)

| Tool | What it does |
|------|-------------|
| `neural_train` | Train MoE/transformer/classifier/embedding models |
| `neural_predict` | Make predictions |
| `neural_patterns` | Store/search/list learned patterns |
| `neural_optimize` | Optimize for speed/memory/accuracy |
| `neural_compress` | Quantize/prune/distill models |
| `neural_status` | Model status |

### 7. AgentDB (ReasoningBank)

| Tool | What it does |
|------|-------------|
| `agentdb_pattern-store` | Store pattern with confidence score |
| `agentdb_pattern-search` | BM25 + semantic hybrid search |
| `agentdb_hierarchical-store/recall` | Hierarchical memory (L1-L4) |
| `agentdb_context-synthesize` | Synthesize context from multiple memories |
| `agentdb_causal-edge` | Track causal relationships |
| `agentdb_feedback` | Record feedback for learning |
| `agentdb_semantic-route` | Route by semantic similarity |

### 8. Other Systems

| Category | Tools |
|----------|-------|
| **Workflow** | create, execute, run, pause, resume, cancel, status, template |
| **Tasks** | create, assign, update, complete, cancel, list, status, summary |
| **Sessions** | save, restore, list, info, delete |
| **Config** | get, set, list, export, import, reset |
| **Performance** | benchmark, profile, metrics, optimize, bottleneck, report |
| **Coordination** | consensus, sync, load_balance, orchestrate, topology, node |
| **Browser** | 20+ automation tools (click, fill, screenshot, eval, etc.) |
| **GitHub** | repo_analyze, pr_manage, issue_track, workflow, metrics |
| **Security** | AIMDS analyze/scan/learn, PII detection |
| **Transfer** | Plugin store, IPFS, PII detection |

---

## How We Should Use Ruflo

### Currently Using (Basic)
- Memory store with 34 entries
- Pattern storage (21 patterns)

### Should Start Using

**1. SONA Trajectory Learning** — Track every GSD phase execution:
```
trajectory-start → "Execute GSD Phase 75: Build Pipeline"
trajectory-step → "Added sse-starlette to deps" (quality: 0.8)
trajectory-step → "Fixed TransferAdapter name" (quality: 0.9)
trajectory-end → success: true
→ Ruflo learns: "build failures often = missing embedded Python deps"
```

**2. MoE Expert Routing** — Let Ruflo route tasks to the right expert:
```
hooks_model-route → "fix EBUSY file lock in CI"
→ Ruflo routes to: devops expert (not coder)
```

**3. Pattern Search Before Acting** — Check if we've seen this before:
```
intelligence_pattern-search → "electron-builder EBUSY"
→ Found: "Model2Vec files get locked on Windows CI, use post-build copy"
```

**4. Embeddings for Code Similarity** — Compare code patterns:
```
embeddings_compare → text1="EBUSY copyfile", text2="resource busy or locked"
→ similarity: 0.92
```

**5. Hive-Mind for Agent Teams** — Shared memory during swarm execution:
```
hive-mind_init → team for GSD phase
hive-mind_memory set → "phase_context: ..."
→ All agents share context without re-reading files
```

---

## Integration with Viking

| Task | Use Viking | Use Ruflo |
|------|-----------|-----------|
| "How does merge work?" | viking_search("merge architecture") | — |
| "Have we seen this bug before?" | — | memory_search("EBUSY file lock") |
| "What pattern should I use?" | viking_search("xml parsing pattern") | pattern-search("xml parsing") |
| "Track this fix for learning" | — | trajectory-start/step/end |
| "Route this task to right agent" | — | hooks_model-route |
| "Find similar code" | — | embeddings_compare |
| "Share context across agents" | — | hive-mind_memory |

**Rule of thumb:** Viking = project knowledge (static). Ruflo = AI experience (dynamic, grows).

---

*Last updated: 2026-03-24*
