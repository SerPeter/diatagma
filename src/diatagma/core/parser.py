"""Read and write spec files (markdown with YAML frontmatter).

Handles the serialization boundary: converts between on-disk spec
files and in-memory Spec/SpecMeta models. Uses python-frontmatter for
parsing and PyYAML for YAML round-tripping.

Key functions:
    parse_spec_file(path)  → Spec
    write_spec_file(spec, path)
    parse_frontmatter(text) → SpecMeta
    render_spec(spec) → str
"""
