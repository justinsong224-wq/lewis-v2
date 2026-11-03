"""中文真实模型推理；英文仍交给原有 Predictor。"""
import re
from functools import lru_cache
from pathlib import Path

import torch

DIRECTORY = Path(__file__).resolve().parent / 'workspace/assets/sms/chinese'


@lru_cache(maxsize=1)
def chinese_predictor():
    from src.model import SMSTransformer
    state = torch.load(DIRECTORY / 'transformer.pt', map_location='cpu', weights_only=True)
    model = SMSTransformer(**state['config'])
    model.load_state_dict(state['model'])
    model.eval()
    return model, state['vocab'], state['config']['max_length']


class LanguagePredictor:
    def __init__(self, english):
        self.english = english

    def predict(self, text):
        if not re.search(r'[\u4e00-\u9fff]', text):
            return self.english.predict(text)
        model, vocab, length = chinese_predictor()
        tokens = re.findall(r'[\u4e00-\u9fff]|[a-z0-9]+|[^\w\s]', text.lower())
        ids = [vocab.get(t, 1) for t in tokens][:length] or [1]
        ids += [0] * (length - len(ids))
        with torch.inference_mode():
            probabilities = model(torch.tensor([ids])).softmax(-1)[0].tolist()
        return dict(label='spam' if probabilities[1] >= .5 else 'ham',
                    spam_probability=probabilities[1], ham_probability=probabilities[0])
