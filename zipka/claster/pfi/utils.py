"""Utility functions for PFI."""
import json
from pathlib import Path

def save_vocab(vocab: dict, path: Path):
    with open(path, 'w') as f:
        json.dump(vocab, f)

def load_vocab(path: Path) -> dict:
    with open(path, 'r') as f:
        return json.load(f)