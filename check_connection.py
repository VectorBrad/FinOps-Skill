"""are we connected — project connection check"""

from pathlib import Path

project_root = Path(__file__).parent

checks = {
    "Git remote":      (project_root / ".git").exists(),
    "CLAUDE.md":       (project_root / "CLAUDE.md").exists(),
    "PROJECT_BRIEF":   (project_root / "PROJECT_BRIEF.md").exists(),
    ".venv":           (project_root / ".venv").exists(),
}

print("\nAre we connected?\n")
all_pass = True
for label, result in checks.items():
    status = "OK" if result else "MISSING"
    print(f"  {status:<8} {label}")
    if not result:
        all_pass = False
print("\nAll good — let's build." if all_pass else "\nFix the above before starting.")
