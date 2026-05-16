# CHANGELOG

<!-- version list -->

## v0.1.0 (2026-05-16)

### Bug Fixes

- **cli**: Resolve encoding crashes, archive listing, and validation errors
  ([`0575074`](https://github.com/SerPeter/diatagma/commit/0575074c47ed67e5fddef8d67da9a130116b2ec6))

### Chores

- Mark DIA-009 and DIA-017 done, add workflow reminder to AGENTS.md
  ([`deb31ac`](https://github.com/SerPeter/diatagma/commit/deb31acbcfeec7f13003903f6bf82148ee675619))

- Mark Phase 1 complete and archive all core library specs
  ([`0ecd723`](https://github.com/SerPeter/diatagma/commit/0ecd7232eeb871d81d4eaed5cb5a7e565afc1665))

### Continuous Integration

- Add GitHub Actions workflows, dependabot, and contributing guide
  ([`e80ff13`](https://github.com/SerPeter/diatagma/commit/e80ff13c0f34568b94e211989de52ec821e5cc91))

### Features

- Scaffold project structure with task system, MCP, and web dashboard
  ([`1031bc2`](https://github.com/SerPeter/diatagma/commit/1031bc2d9d24108c4b00851252394a4b27e7caae))

- **cli**: Add AGENTS.md, CLI skill generation, and expanded init scaffolding (DIA-017)
  ([`9d7b6d0`](https://github.com/SerPeter/diatagma/commit/9d7b6d095e0522eb85b29ff84a71f3f2fc4e047f))

- **cli**: Add roadmap generation and archive parent/cycle filters (DIA-024)
  ([`e746dd7`](https://github.com/SerPeter/diatagma/commit/e746dd7be63c332c51dafdb9b89d631cfede789e))

- **cli**: Implement CLI interface with shared bootstrap layer (DIA-020)
  ([`76d6e21`](https://github.com/SerPeter/diatagma/commit/76d6e213e78cab832496be24ddb411e5b996dab2))

- **core**: Add implementation summary field and archive warning (DIA-019)
  ([`217791f`](https://github.com/SerPeter/diatagma/commit/217791fb90f27e324bd40f6a70f171525148d07f))

- **core**: Auto-regenerate ROADMAP.md on status change
  ([`2d22c7a`](https://github.com/SerPeter/diatagma/commit/2d22c7ad8c3c9c5967b9215cf163cfe0ae7e3fc2))

- **core**: Detect and resolve spec ID collisions after git merge (DIA-016)
  ([`d84fbad`](https://github.com/SerPeter/diatagma/commit/d84fbade0d2a098e3d7b14a647c04d632aacbff7))

- **core**: Implement append-only changelog tracking (DIA-007)
  ([`8a40171`](https://github.com/SerPeter/diatagma/commit/8a401713e2bad11e6685c5362278561a5952da70))

- **core**: Implement file watcher for live spec change detection (DIA-018)
  ([`d2b0c39`](https://github.com/SerPeter/diatagma/commit/d2b0c39ea9bd14005b5f5e9259db49de90f0d292))

- **core**: Implement get_next query for priority-ranked actionable specs (DIA-015)
  ([`c0915da`](https://github.com/SerPeter/diatagma/commit/c0915da5a682a3b58c7809333a8c10f2462dcb4e))

- **core**: Implement lifecycle automation engine (DIA-021)
  ([`4f44e75`](https://github.com/SerPeter/diatagma/commit/4f44e7538683db149dc8bd98b222c2ca4c8f3621))

- **core**: Implement markdown+YAML frontmatter parser (DIA-002)
  ([`8c7f572`](https://github.com/SerPeter/diatagma/commit/8c7f572e281f3659b34f16c1c9c26a2ae376dad7))

- **core**: Implement Pydantic models for specs and configuration (DIA-001)
  ([`2ab9a0d`](https://github.com/SerPeter/diatagma/commit/2ab9a0d9d6dc93401e8e4a0b1b74371a2864319a))

- **core**: Implement SpecStore CRUD over filesystem (DIA-003)
  ([`86dd68d`](https://github.com/SerPeter/diatagma/commit/86dd68dc750875a24ed554b993a5b42bcfc94f48))

- **core**: Implement SQLite read cache with mtime invalidation (DIA-004)
  ([`ad439d8`](https://github.com/SerPeter/diatagma/commit/ad439d8173e1c7b956713bcbb1a3cb3b8514032b))

- **core**: Implement typed dependency graph with SpecLinks model (DIA-014)
  ([`65fcbdc`](https://github.com/SerPeter/diatagma/commit/65fcbdc22b7beb877ca4f15254f91cb4261b9980))

- **core**: Implement WSJF priority scoring and task ranking (DIA-006)
  ([`9dcde7b`](https://github.com/SerPeter/diatagma/commit/9dcde7bb472186408890718a4d66c33c1a411711))

- **core**: Implement YAML configuration loader (DIA-008)
  ([`d252786`](https://github.com/SerPeter/diatagma/commit/d252786b24015931f22096f0397f27db2f7a03c8))

- **mcp**: Implement FastMCP server with tools, resources, and prompts (DIA-009)
  ([`6390f8b`](https://github.com/SerPeter/diatagma/commit/6390f8bc8cf84fcc7ae1f1717acfdd60b7fe2cb2))

- **tasks**: Add research-driven specs, update roadmap, polish config
  ([`c0be3dc`](https://github.com/SerPeter/diatagma/commit/c0be3dc95aedcb72152eb313e9b894cba673f76e))

### Refactoring

- Rename sprint→cycle and .tasks→.specs (DIA-023)
  ([`0bcbe14`](https://github.com/SerPeter/diatagma/commit/0bcbe142c8f3e69c8817a409d963af22aa5f45f9))

- Rename task→story/spec, switch to Litestar+React, add docs structure
  ([`0b343b9`](https://github.com/SerPeter/diatagma/commit/0b343b9e6a704610a51053c75b574705a54a7150))

- **core**: Review cleanup — fix code smells and remove fragile tests
  ([`8768c5c`](https://github.com/SerPeter/diatagma/commit/8768c5c8362e37dad79a769264fe4af724e15f05))
