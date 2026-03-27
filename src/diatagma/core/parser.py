"""Read and write markdown files with YAML frontmatter.

Handles the serialization boundary: converts between on-disk markdown
files and in-memory Task/TaskMeta models. Uses python-frontmatter for
parsing and PyYAML for YAML round-tripping.

Key functions:
    parse_task_file(path)  → Task
    write_task_file(task, path)
    parse_frontmatter(text) → TaskMeta
    render_task(task) → str
"""
