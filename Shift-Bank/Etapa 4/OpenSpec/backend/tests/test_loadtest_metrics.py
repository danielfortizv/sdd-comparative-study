import ast
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from loadtest.metrics import ensure_isolated_database, is_steady_sample, observed_distribution, percentile, strict_below


class LoadTestMetricsTest(unittest.TestCase):
    def test_isolation_guard_accepts_only_run_owned_database_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(root / "synthetic.sqlite3", ensure_isolated_database(root / "synthetic.sqlite3", root, root / "backend" / "bank.db"))
            with self.assertRaisesRegex(ValueError, "non-isolated"):
                ensure_isolated_database(root.parent / "historical.sqlite3", root, root / "backend" / "bank.db")
            with self.assertRaisesRegex(ValueError, "non-isolated"):
                ensure_isolated_database(root / "backend" / "bank.db", root, root / "backend" / "bank.db")

    def test_observed_distribution_uses_request_samples(self):
        requests = ([{"name": "balance_read"}] * 6 + [{"name": "history_read"}] * 3 + [{"name": "internal_transfer"}])
        distribution = observed_distribution(requests)
        self.assertEqual(60.0, distribution["balance_read"]["percentage"])
        self.assertEqual(30.0, distribution["history_read"]["percentage"])
        self.assertEqual(10.0, distribution["internal_transfer"]["percentage"])

    def test_steady_boundary_excludes_ramp_and_end_timestamp(self):
        self.assertFalse(is_steady_sample({"start_time": 10.0}, 20.0, 80.0))
        self.assertTrue(is_steady_sample({"start_time": 20.0}, 20.0, 80.0))
        self.assertFalse(is_steady_sample({"start_time": 80.0}, 20.0, 80.0))

    def test_nearest_rank_percentile_and_strict_slo_equality(self):
        self.assertEqual(95.0, percentile([float(value) for value in range(1, 101)], 0.95))
        self.assertTrue(strict_below(199.999, 200.0))
        self.assertFalse(strict_below(200.0, 200.0))
        self.assertFalse(strict_below(None, 200.0))

    def test_locust_task_weights_encode_the_approved_profile(self):
        locust_path = Path(__file__).resolve().parents[1] / "loadtest" / "locustfile.py"
        module = ast.parse(locust_path.read_text(encoding="utf-8"))
        weights = {}
        for node in module.body:
            if isinstance(node, ast.ClassDef) and node.name == "ShiftBankUser":
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        for decorator in method.decorator_list:
                            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "task":
                                weights[method.name] = decorator.args[0].value
        self.assertEqual({"read_balance": 6, "read_history": 3, "transfer": 1}, weights)


if __name__ == "__main__":
    unittest.main()
