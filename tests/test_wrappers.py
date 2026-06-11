"""Shape checks for the root-level REPL wrapper scripts.

The wrappers (README "Running on the air-gapped target machine") are
exec()'d in the WinPython REPL on the target, so they are never imported
or executed here — their hardcoded C:\\ paths would not resolve on the
dev host. Instead these tests parse the source: each wrapper must stay
stdlib-only, target an existing canonical script under scripts/, hand it
sys.argv via runpy.run_path(run_name="__main__"), and never chdir (the
operator chdirs once, by hand).
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# wrapper at ROOT -> the canonical script under scripts/ it must target
WRAPPERS = {
    "extract.py": "extract_to_csv.py",
    "dedupe.py": "deduplicate_csv.py",
    "write.py": "generate_dita.py",
    "publish.py": "publish_html.py",
    "introspect.py": "introspect_pptx.py",
    "snapshot.py": "snapshot_analysis_docs.py",
}

ALLOWED_IMPORTS = {"os", "sys", "runpy", "pathlib"}


def _tree(name: str) -> ast.Module:
    return ast.parse((REPO_ROOT / name).read_text(encoding="utf-8"))


def _imported_top_modules(tree: ast.Module) -> set:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.add(node.module.split(".", 1)[0])
    return names


def _py_path_literals(tree: ast.Module) -> set:
    """Every ``<expr> / "<name>.py"`` path component in the module."""
    found = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                and isinstance(node.right, ast.Constant)
                and isinstance(node.right.value, str)
                and node.right.value.endswith(".py")):
            found.add(node.right.value)
    return found


def _calls(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def _dotted(func) -> str:
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    if isinstance(func, ast.Name):
        return func.id
    return ""


class WrapperShapeTests(unittest.TestCase):

    def test_wrappers_exist(self) -> None:
        for wrapper in WRAPPERS:
            self.assertTrue((REPO_ROOT / wrapper).is_file(),
                            f"missing root wrapper: {wrapper}")

    def test_wrappers_import_only_the_stdlib(self) -> None:
        for wrapper in WRAPPERS:
            imported = _imported_top_modules(_tree(wrapper))
            self.assertLessEqual(
                imported, ALLOWED_IMPORTS,
                f"{wrapper} imports beyond the wrapper allowance: "
                f"{sorted(imported - ALLOWED_IMPORTS)}")

    def test_wrappers_target_their_existing_canonical_script(self) -> None:
        for wrapper, canonical in WRAPPERS.items():
            referenced = _py_path_literals(_tree(wrapper))
            self.assertEqual(
                referenced, {canonical},
                f"{wrapper} must reference exactly its canonical script")
            self.assertTrue((REPO_ROOT / "scripts" / canonical).is_file(),
                            f"{wrapper} targets a missing scripts/{canonical}")

    def test_wrappers_run_the_canonical_script_as_main(self) -> None:
        for wrapper in WRAPPERS:
            runs = [
                call for call in _calls(_tree(wrapper))
                if _dotted(call.func) == "runpy.run_path"
                and any(kw.arg == "run_name"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value == "__main__"
                        for kw in call.keywords)
            ]
            self.assertTrue(
                runs,
                f"{wrapper} never calls runpy.run_path(run_name='__main__')")

    def test_wrappers_set_sys_argv(self) -> None:
        for wrapper in WRAPPERS:
            assigns = [
                node for node in ast.walk(_tree(wrapper))
                if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Attribute) and t.attr == "argv"
                        and isinstance(t.value, ast.Name)
                        and t.value.id == "sys"
                        for t in node.targets)
            ]
            self.assertTrue(assigns, f"{wrapper} never assigns sys.argv")

    def test_wrappers_never_chdir(self) -> None:
        # The operator chdirs once, by hand; wrappers must not bake it in.
        for wrapper in WRAPPERS:
            for call in _calls(_tree(wrapper)):
                self.assertNotEqual(_dotted(call.func), "os.chdir",
                                    f"{wrapper} must not chdir")


if __name__ == "__main__":
    unittest.main()
