from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    import torch
    import train_guidematch as train
except ImportError:
    torch = None

@unittest.skipIf(torch is None, 'training dependencies are not installed')
class ResumeTests(unittest.TestCase):
    def test_interrupted_epoch_resume_matches_uninterrupted_training(self):
        class Tokenizer:
            @classmethod
            def from_pretrained(cls, source): return cls()
            def __call__(self, left, right, **kwargs):
                return {'input_ids': torch.tensor([[len(a) % 5 + 1, len(b) % 5 + 1] for a, b in zip(left, right)])}
            def save_pretrained(self, output): Path(output).mkdir(parents=True, exist_ok=True)
        class Encoder(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.embedding = torch.nn.Embedding(7, 4)
                self.config = type("Config", (), {"save_pretrained": lambda self, output: Path(output).mkdir(parents=True, exist_ok=True)})()
            def save_pretrained(self, output): Path(output).mkdir(parents=True, exist_ok=True)
        class Model(torch.nn.Module):
            def __init__(self, source, num_labels, num_reasons, dropout):
                super().__init__(); self.encoder = Encoder(); self.label_head = torch.nn.Linear(4, num_labels); self.reason_head = torch.nn.Linear(4, num_reasons)
            def configure_stage(self, stage): return {'stage': stage}
            def forward(self, input_ids):
                x = self.encoder.embedding(input_ids).mean(dim=1)
                return self.label_head(x), self.reason_head(x)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'data/splits').mkdir(parents=True)
            rows = [{'case_id': str(i), 'left': {'text': '左' * (i+1)}, 'right': {'text': '右'}, 'expected': ['reuse','distinct','clarify'][i%3], 'reason': 'same_target'} for i in range(6)]
            for name in ('train','dev'):
                (root / 'data/splits' / f'{name}.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows))
            config = {'labels':['reuse','distinct','clarify'], 'reasons':['same_target'], 'require_cuda':False, 'augment_swap':False, 'dropout':0.0, 'max_length':16, 'batch_size':2, 'num_workers':0, 'learning_rate_head':0.01, 'learning_rate_encoder':0.01, 'weight_decay':0.0, 'gradient_accumulation_steps':1, 'epochs':3, 'label_smoothing':0.0, 'aux_loss_weight':0.25, 'false_reuse_penalty':0.35, 'max_grad_norm':1.0, 'selection_metric':'macro_f1', 'early_stopping_patience':10}
            (root / 'config.json').write_text(json.dumps(config))
            def invoke(out, extra=()):
                argv = ['train', '--config', str(root/'config.json'), '--model-source', 'fixture', '--stage', 'frozen', '--seed', '13', '--output-dir', str(out), *extra]
                with patch.object(sys, 'argv', argv): return train.main()
            with patch.object(train, 'root_dir', return_value=root), patch.object(train, 'AutoTokenizer', Tokenizer), patch.object(train, 'GuideMatchModel', Model):
                invoke(root/'full')
                original_eval = train.evaluate; calls = 0
                def interrupted(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2: raise RuntimeError('simulated interruption')
                    return original_eval(*args, **kwargs)
                with patch.object(train, 'evaluate', side_effect=interrupted):
                    with self.assertRaisesRegex(RuntimeError, 'simulated interruption'): invoke(root/'resumed')
                checkpoint = root/'resumed/checkpoint.pt'
                self.assertTrue(checkpoint.exists())
                invoke(root/'resumed', ['--resume-from', str(checkpoint)])
                a = torch.load(root/'full/model.pt', weights_only=True)['state_dict']
                b = torch.load(root/'resumed/model.pt', weights_only=True)['state_dict']
                for key in a: self.assertTrue(torch.equal(a[key], b[key]), key)
                config['batch_size'] = 3; (root/'config.json').write_text(json.dumps(config))
                with self.assertRaisesRegex(ValueError, 'configuration or training data'):
                    invoke(root/'resumed', ['--resume-from', str(checkpoint)])

if __name__ == '__main__': unittest.main()
