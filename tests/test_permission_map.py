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

PER_ROW_PLAN = r"""# Authorization — Design

## 2. Permission catalogue

| Feature | Note |
|---|---|
| Sign in, sign out | every user |

### Permission-gated

| Permission | A | B | C |
|---|:-:|:-:|:-:|
| `users.create` | ✔ | ✔¹ | — |
| `users.delete` | ✔ | — | — |
| `shelves.create` / `.edit` / `.list` | ✔ | — | — |
| `sites.create` | ✔ | ✔ | — |
| `sites.view` | ✔ | ✔ | — |
| `places.*` | *identical to sites* | | |
| `inventory.bins.create` / `.read` / `.delete` | ✔ | ✔ | — |

¹ Footnotes are not rows: `users.grant` is not read.

| Matrix row | A | B | C | Permission |
|---|:-:|:-:|:-:|---|
| *(no row — the menu item)* | ✔ | ✔ | ✔ | `planner.list` — ours, held with `tasks.edit` |
| View tasks | ✔ | ✔ | ✔ | `planner.tasks.list`, `planner.tasks.view` |
| Filter | ✔ | — | — | none — a rule on `planner.rules` |
| Certificates | ✔ | ✔ | — | `certs.<alpha\|beta>.list`, `.view` |
| Linked note | ✔ | — | — | see [users.md](users.md) and `users.md` |

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

    def test_an_action_after_a_dash_is_a_note_not_an_action(self):
        plan = PLAN.replace("| `bins` | `list`, `delete` |", "| `bins` | `list`, `delete` — no `setstatus`: a field |")
        self.assertNotIn("bins.setstatus", permission_map.plan_permissions(plan))

    def test_one_permission_per_row_with_role_columns(self):
        found = permission_map.plan_permissions(PER_ROW_PLAN)
        self.assertEqual(found, {
            "users.create", "users.delete",
            "shelves.create", "shelves.edit", "shelves.list",
            "sites.create", "sites.view", "places.create", "places.view",
            "inventory.bins.create", "inventory.bins.read", "inventory.bins.delete",
            "planner.list", "planner.tasks.list", "planner.tasks.view",
            "certs.alpha.list", "certs.beta.list", "certs.alpha.view", "certs.beta.view",
        })

    def test_the_per_row_shape_is_compared_with_the_code_whole(self):
        catalogue = CATALOGUE.replace('public const string List = "bins.list";',
                                      'public const string Read = "inventory.bins.read";')
        out, code = self.run_map(self.project(plan=PER_ROW_PLAN, catalogue=catalogue, contracts=None),
                                 catalogue=Path("src/App/Permissions.cs"))
        self.assertEqual(code, 0)
        self.assertIn("Plan docs/plans/authorization.md: 19 permissions.", out)
        self.assertIn("In the code, not in plan §2: orders.cancel, orders.create, orders.list, orders.view", out)
        missing = out.split("In plan §2, not in the code: ")[1].split("\n")[0].split(", ")
        self.assertIn("inventory.bins.create", missing)
        self.assertNotIn("inventory.bins.read", missing)

    def test_a_multi_dot_permission_groups_under_its_module(self):
        catalogue = CATALOGUE.replace('public const string List = "bins.list";',
                                      'public const string Read = "inventory.bins.read";')
        contracts = CONTRACTS + "| GET | `/api/v1/bins` | `inventory.bins.read` | — | 200 | `ListBinsQuery` |\n"
        out, _ = self.run_map(self.project(catalogue=catalogue, contracts=contracts))
        self.assertIn("- inventory.bins\n  - read: GET /api/v1/bins", out)

    def test_a_section_two_with_no_permission_blocks(self):
        plan = PLAN.replace("| `orders` | `list`, `view`, `create` |\n| `bins` | `list`, `delete` |\n",
                            "| Orders — list, view | yes |\n")
        self.assertEqual(permission_map.plan_permissions(plan), set())
        out, code = self.run_map(self.project(plan=plan))
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED: section 2 of docs/plans/authorization.md yields no permission", out)

    def test_a_missing_plan_or_catalogue_blocks(self):
        out, code = self.run_map(self.project(plan=None))
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED: no plan", out)
        out, code = self.run_map(self.project(contracts=None))
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED: the code's permission catalogue was not found", out)


if __name__ == "__main__":
    unittest.main()
