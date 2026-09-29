import json
import tempfile
import time
import unittest
from pathlib import Path

from filelock import FileLock, Timeout
from browser_task_helper.config import Config
from browser_task_helper.runtime import Reporter, write_json

class CoreTests(unittest.TestCase):
    def test_configuration_requires_real_count_and_secure_url(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for url,count in [('https://example.org/',0),('http://example.org/',1),('https://u:p@example.org/',1)]:
                with self.subTest(url=url,count=count),self.assertRaises(ValueError):
                    Config(url=url,expected_videos=count,state_dir=root).validate()
            Config(url='http://127.0.0.1:3456/',expected_videos=2,state_dir=root).validate()

    def test_relative_paths_and_unknown_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config.toml'
            path.write_text('url="https://example.org/"\nexpected_videos=2\nstate_dir="private"\n')
            self.assertEqual(Config.load(path).state_dir,(path.parent/'private').resolve())
            path.write_text(path.read_text()+'unexpected=true\n')
            with self.assertRaises(TypeError):Config.load(path)

    def test_state_transitions_keep_age_and_emit_only_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);report=Reporter(root)
            report('loading');start=report.latest['state_since']
            report('loading');self.assertEqual(report.latest['state_since'],start)
            report('playing',lesson='1.1',media={'duration':float('nan')})
            data=json.loads((root/'status.json').read_text(),parse_constant=lambda x:self.fail(x))
            self.assertIsNone(data['media']['duration'])
            self.assertEqual(len((root/'events.jsonl').read_text().splitlines()),2)

    def test_single_instance_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            name=str(Path(directory)/'runner.lock')
            with FileLock(name,timeout=0):
                with self.assertRaises(Timeout):
                    with FileLock(name,timeout=0):pass
