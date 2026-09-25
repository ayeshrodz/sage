import hashlib
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("model_parts", Path(__file__).resolve().parents[1] / "tools" / "model_parts.py")
model_parts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model_parts)


class ModelPartsTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.src = self.dir / "model.gguf"
        self.data = os.urandom(10_000)
        self.src.write_bytes(self.data)

    def test_split_then_join_rebuilds_the_file(self):
        digest = model_parts.split(self.src, self.dir / "parts", 3_000)
        self.assertEqual(digest, hashlib.sha256(self.data).hexdigest())
        self.assertEqual(len(list((self.dir / "parts").glob("model.gguf.part*"))), 4)
        self.assertEqual(model_parts.join(self.dir / "parts", self.dir / "out.gguf"), digest)
        self.assertEqual((self.dir / "out.gguf").read_bytes(), self.data)

    def test_join_refuses_a_corrupt_or_missing_part(self):
        model_parts.split(self.src, self.dir / "parts", 3_000)
        part = self.dir / "parts" / "model.gguf.part001"
        part.write_bytes(b"x" + part.read_bytes()[1:])
        with self.assertRaises(ValueError):
            model_parts.join(self.dir / "parts", self.dir / "out.gguf")
        part.unlink()
        with self.assertRaises(OSError):
            model_parts.join(self.dir / "parts", self.dir / "out.gguf")
        self.assertEqual(list(self.dir.glob("out.gguf*")), [])  # nothing left behind


if __name__ == "__main__":
    unittest.main()
