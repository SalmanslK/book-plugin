"""
Self-tests for check-permissions' permission_map.py: the plan's catalogue, the code's catalogue and the
generated contracts, set against each other. Each test builds a throwaway project; standard library only.
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins" / "book" / "skills" / "check-permissions" / "scripts" / \
    "permission_map.py"
spec = importlib.util.spec_from_file_location("permission_map", SCRIPT)
permission_map = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permission_map)

PLAN = """# Authorization — Design

## 1. Recommendation

| `ignored` | `not`, `section`, `two` |

## 2. Permission catalogue

### Permission-gated

| Module | Actions |
|---|---|
| `orders` | `list`, `view`, `create` |
| `bins` | `list`, `delete` |

## 3. Adding a module's permissions
"""

CATALOGUE = """public static class Permissions
{
    public static class Orders
    {
        public const string List = "orders.list";
        public const string View = "orders.view";
        public const string Create = "orders.create";
        public const string Cancel = "orders.cancel";
    }
    public static class Bins
    {
        public const string List = "bins.list";
    }
}
"""

CONTRACTS = """# API contracts

**5 routes** across **2 endpoint groups** — 1 anonymous, 1 authenticated-only, 3 permission-gated.

- **Auth** — a permission string is what the request declares (the catalogue is
  `src/App/Permissions.cs`); `authenticated` means the fallback policy.

| Verb | Path | Auth | Request | Responses | Dispatches |
|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | anonymous | body: `LoginRequest` | 200 | `LoginCommand` |
| GET | `/api/v1/orders/lookup` | authenticated | — | 200 | `LookupOrdersQuery` |
| GET | `/api/v1/orders` | `orders.list` | — | 200 | `ListOrdersQuery` |
| GET | `/api/v1/orders/{id:long}` | `orders.view` | route: `id` | 200<br>404 | `GetOrderQuery` |
| POST | `/api/v1/bins/purge` | `bins.purge` | — | 204 | `PurgeBinsCommand` |
"""


class PermissionMapTests(unittest.TestCase):
    def project(self, plan: str | None = PLAN, catalogue: str | None = CATALOGUE,
                contracts: str | None = CONTRACTS) -> Path:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        for rel, text in (("docs/plans/authorization.md", plan), ("src/App/Permissions.cs", catalogue),
                          ("docs/api/api-contracts.md", contracts)):
            if text is not None:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding="utf-8")
        return root

    def run_map(self, root: Path, **kwargs) -> tuple[str, int]:
        lines, code = permission_map.report(root, Path("docs/plans/authorization.md"),
                                            Path("docs/api/api-contracts.md"), kwargs.get("catalogue"))
        return "\n".join(lines), code

    def test_only_section_two_of_the_plan_is_read(self):
        self.assertEqual(permission_map.plan_permissions(PLAN),
                         {"orders.list", "orders.view", "orders.create", "bins.list", "bins.delete"})

    def test_the_catalogue_differences_both_ways(self):
        out, code = self.run_map(self.project())
        self.assertEqual(code, 0)
        self.assertIn("In the code, not in plan §2: orders.cancel", out)
        self.assertIn("In plan §2, not in the code: bins.delete", out)

    def test_routes_against_the_catalogue(self):
        out, _ = self.run_map(self.project())
        self.assertIn("Declared by a route, not in the code's catalogue: bins.purge", out)
        self.assertIn("In the catalogue, gating no route: bins.list, orders.cancel, orders.create", out)
        self.assertIn("  - view: GET /api/v1/orders/{id:long}", out)

    def test_open_routes_are_listed_and_the_counts_agree(self):
        out, _ = self.run_map(self.project())
        self.assertIn("Routes any signed-in user may call (no permission): 1\n- GET /api/v1/orders/lookup → "
                      "LookupOrdersQuery", out)
        self.assertIn("Anonymous routes: 1\n- POST /api/v1/auth/login → LoginCommand", out)
        self.assertNotIn("MISMATCH", out)

    def test_a_count_mismatch_is_flagged(self):
        out, _ = self.run_map(self.project(contracts=CONTRACTS.replace("3 permission-gated", "4 permission-gated")))
        self.assertIn("MISMATCH", out)

    def test_without_contracts_only_the_catalogue_is_compared(self):
        out, code = self.run_map(self.project(contracts=None), catalogue=Path("src/App/Permissions.cs"))
        self.assertEqual(code, 0)
        self.assertIn("In plan §2, not in the code: bins.delete", out)
        self.assertIn("route comparisons are skipped", out)

    def test_a_missing_plan_or_catalogue_blocks(self):
        out, code = self.run_map(self.project(plan=None))
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED: no plan", out)
        out, code = self.run_map(self.project(contracts=None))
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED: the code's permission catalogue was not found", out)


if __name__ == "__main__":
    unittest.main()
