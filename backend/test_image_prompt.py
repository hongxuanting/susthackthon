import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("MOCK_AI", "true")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents_core import _extract_image_prompt


class ImagePromptTests(unittest.TestCase):
    def test_extracts_compact_scene_prompt(self):
        scene = "你站在迷雾小镇的广场上，远处教堂钟声回荡，街道尽头有一个黑影注视着你。"

        prompt = _extract_image_prompt(scene)

        self.assertLessEqual(len(prompt), 10)
        self.assertTrue(prompt)

    def test_removes_filler_and_limits_prompt(self):
        scene = "abc123你躲在倒塌的砖块后面，观察废弃超市门口的动静。"

        prompt = _extract_image_prompt(scene)

        self.assertLessEqual(len(prompt), 10)
        self.assertIn("砖块", prompt)
        self.assertIn("超市", prompt)


if __name__ == "__main__":
    unittest.main()
