"""中文字符级 Transformer 与 TF-IDF + LogisticRegression，同划分真实评估。"""
import argparse
import copy
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'backend/workspace/assets/sms'
sys.path.insert(0, str(ASSETS))
from src.model import SMSTransformer


def tokens(text):
    return re.findall(r'[\u4e00-\u9fff]|[a-z0-9]+|[^\w\s]', text.lower())


def encode(text, vocab, length):
    ids = [vocab.get(t, 1) for t in tokens(text)][:length] or [1]
    return ids + [0] * (length - len(ids))


def scores(y, predictions):
    p, r, f, _ = precision_recall_fscore_support(y, predictions, average='binary', zero_division=0)
    return dict(accuracy=float(accuracy_score(y, predictions)), precision=float(p), recall=float(r),
                f1=float(f), confusion_matrix=confusion_matrix(y, predictions, labels=[0, 1]).tolist())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    parser.add_argument('--epochs', type=int, default=15)
    parser.add_argument('--per-class', type=int, default=10000)
    args = parser.parse_args()
    torch.manual_seed(42); np.random.seed(42); random.seed(42)
    torch.set_num_threads(4)
    path = Path(args.data)
    if path.suffix == '.csv':
        raw = pd.read_csv(path).rename(columns={'content': 'text'})[['text', 'label']]
    else:
        rows = []
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                # public mudou file: label TAB message, or id TAB label TAB message
                if parts[0] in ('0', '1'):
                    rows.append((parts[1], int(parts[0])))
                elif len(parts) == 3 and parts[1] in ('0', '1'):
                    rows.append((parts[2], int(parts[1])))
        raw = pd.DataFrame(rows, columns=['text', 'label'])
    raw = raw.dropna().copy()
    raw['text'] = raw.text.astype(str).map(lambda s: re.sub(r'\s+', ' ', s).strip())
    raw['label'] = raw.label.astype(int)
    raw = raw[raw.label.isin([0, 1]) & raw.text.str.len().between(3, 5000)]
    raw['key'] = raw.text.str.lower()
    conflicts = raw.groupby('key').label.nunique()
    raw = raw[~raw.key.isin(conflicts[conflicts > 1].index)].drop_duplicates('key')
    # Demonstration texts never enter train/validation/test.
    demo = pd.read_csv(ROOT / 'demo/sms-classifier/messages.csv').text.str.lower()
    raw = raw[~raw.key.isin(demo)]
    frame = raw.groupby('label', group_keys=False).apply(lambda g: g.sample(min(len(g), args.per_class), random_state=42)).reset_index(drop=True)
    if frame.label.nunique() != 2 or frame.label.value_counts().min() < 50:
        raise ValueError('Both classes need at least 50 independent samples')
    train, rest = train_test_split(frame, test_size=.3, stratify=frame.label, random_state=42)
    valid, test = train_test_split(rest, test_size=.5, stratify=rest.label, random_state=42)
    print('data', len(train), len(valid), len(test), frame.label.value_counts().to_dict(), flush=True)
    baseline = make_pipeline(TfidfVectorizer(analyzer='char', ngram_range=(1, 3), max_features=30000, sublinear_tf=True), LogisticRegression(max_iter=500, class_weight='balanced', random_state=42))
    baseline.fit(train.text, train.label)
    baseline_metrics = scores(test.label, baseline.predict(test.text))
    vocab = {'<pad>': 0, '<unk>': 1}
    for token, _ in Counter(t for text in train.text for t in tokens(text)).most_common(7998):
        vocab[token] = len(vocab)
    config = dict(vocab_size=len(vocab), max_length=192, d_model=64, nhead=4, dim_feedforward=128, num_layers=1, dropout=.15)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SMSTransformer(**config).to(device)
    def loader(part, shuffle=False):
        return DataLoader(TensorDataset(torch.tensor([encode(t, vocab, 192) for t in part.text]), torch.tensor(part.label.to_numpy())), batch_size=128, shuffle=shuffle)
    def evaluate(part):
        model.eval(); result = []
        with torch.inference_mode():
            for x, _ in loader(part): result.extend(model(x.to(device)).argmax(1).cpu().tolist())
        return scores(part.label, result)
    weights = len(train) / (2 * np.bincount(train.label, minlength=2))
    loss_fn = torch.nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.01)
    best_f1 = -1; best = None; best_epoch = 0; history = []; started = time.monotonic()
    for epoch in range(args.epochs):
        model.train(); total = 0
        for x, y in loader(train, True):
            optimizer.zero_grad(); loss = loss_fn(model(x.to(device)), y.to(device)); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1); optimizer.step(); total += loss.item()
        value = evaluate(valid)
        history.append(dict(epoch=epoch+1, validation=value, loss=total))
        print('epoch', epoch+1, 'validation', value, flush=True)
        if value['f1'] > best_f1:
            best_f1 = value['f1']; best = copy.deepcopy(model.state_dict()); best_epoch = epoch+1
        if epoch+1-best_epoch >= 4: break
    model.load_state_dict(best)
    transformer_metrics = evaluate(test)
    out = ASSETS / 'chinese'; out.mkdir(exist_ok=True)
    torch.save(dict(model={k:v.cpu() for k,v in best.items()}, vocab=vocab, config=config, tokenizer='chinese-character-v1'), out/'transformer.pt')
    metrics = dict(baseline=baseline_metrics, transformer=transformer_metrics, best_epoch=best_epoch,
                   best_validation_f1=best_f1, training_seconds=round(time.monotonic()-started,2), history=history)
    stats = dict(source='Public Chinese SMS corpus (see provenance.json)', language='zh', cleaned_rows=len(frame), ham=int((frame.label==0).sum()), spam=int((frame.label==1).sum()), train=len(train), validation=len(valid), test=len(test), seed=42, config=config, vocab_size=len(vocab), device=str(device), torch_version=torch.__version__, parameters=sum(p.numel() for p in model.parameters()), data_sha256=hashlib.sha256(frame[['text','label']].to_csv(index=False).encode()).hexdigest(), splits={name:hashlib.sha256(p[['text','label']].to_csv(index=False).encode()).hexdigest() for name,p in [('train',train),('validation',valid),('test',test)]}, demo_excluded=True, baseline='Character TF-IDF (1-3 grams) + LogisticRegression')
    for name, data in [('metrics.json',metrics),('dataset_stats.json',stats)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    provenance = dict(source_file=str(path), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), dataset_stats=stats, scope='New local Chinese training; not part of historical Lewis generation', checkpoint_sha256=hashlib.sha256((out/'transformer.pt').read_bytes()).hexdigest())
    (out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in metrics.items() if k!='history'}),flush=True)


if __name__ == '__main__': main()
