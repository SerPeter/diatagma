"""Tests for core.checkbox — task-list progress parsing."""

from diatagma.core.checkbox import count_checkboxes


class TestCountCheckboxes:
    def test_counts_checked_and_total(self):
        text = "- [x] one\n- [ ] two\n- [x] three\n- [ ] four\n- [ ] five"
        assert count_checkboxes(text) == (2, 5)

    def test_uppercase_x(self):
        assert count_checkboxes("- [X] done") == (1, 1)

    def test_placeholder_excluded(self):
        assert count_checkboxes("- [ ] ...") == (0, 0)

    def test_mixed_placeholder_and_real(self):
        assert count_checkboxes("- [ ] real item\n- [ ] ...") == (0, 1)

    def test_asterisk_bullets(self):
        assert count_checkboxes("* [x] a\n* [ ] b") == (1, 2)

    def test_indented_nested(self):
        text = "- [x] parent\n  - [ ] child\n  - [x] child2"
        assert count_checkboxes(text) == (2, 3)

    def test_none_and_empty(self):
        assert count_checkboxes(None) == (0, 0)
        assert count_checkboxes("") == (0, 0)

    def test_non_checkbox_lines_ignored(self):
        text = "## Heading\nsome prose\n- regular bullet\n- [x] task"
        assert count_checkboxes(text) == (1, 1)
