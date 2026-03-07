#!/usr/bin/env python3
"""Embed nodes and build a vector index (Faiss if available, else sklearn fallback).

Usage:
  python embed_and_index.py --input kg_nodes.json --outdir index --limit 200
"""
import os
import json
import argparse
import numpy as np
import pickle

def load_nodes(path, limit=None):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if limit:
        data = data[:limit]
    docs = []
    for item in data:
        nid = item.get('id')
        labels = item.get('labels', [])
        props = item.get('props', {})
        name = props.get('实体名称') or item.get('props', {}).get('实体名称') or ''
        # build text
        parts = [f"Name: {name}"] if name else []
        if labels:
            parts.append('Labels: ' + ', '.join(labels))
        # include some props
        for k, v in props.items():
            parts.append(f"{k}: {v}")
        text = '\n'.join(parts)
        docs.append({'id': nid, 'text': text, 'name': name, 'labels': labels, 'props': props})
    return docs

def get_embeddings(texts, model_name='sentence-transformers/all-MiniLM-L6-v2'):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError('请先安装 sentence-transformers：pip install sentence-transformers')
    model = SentenceTransformer(model_name)
    emb = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return emb

def build_faiss_index(embeddings, outdir):
    try:
        import faiss
        d = embeddings.shape[1]
        index = faiss.IndexFlatIP(d)
        # normalize for cosine
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        faiss.write_index(index, os.path.join(outdir, 'kg_index.faiss'))
        return 'faiss'
    except Exception:
        # fallback: save numpy embeddings and use sklearn at query time
        np.save(os.path.join(outdir, 'kg_embeddings.npy'), embeddings)
        return 'numpy'

def save_docstore(docs, outdir):
    with open(os.path.join(outdir, 'kg_docstore.pkl'), 'wb') as f:
        pickle.dump(docs, f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='kg_nodes.json')
    parser.add_argument('--outdir', default='index')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2')
    args = parser.parse_args()

    inp = args.input
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)

    docs = load_nodes(inp, limit=args.limit or None)
    if not docs:
        print('No docs loaded from', inp)
        return

    texts = [d['text'] or d['name'] or '' for d in docs]
    print(f'Embedding {len(texts)} docs using model {args.model}...')
    emb = get_embeddings(texts, model_name=args.model)
    print('Embeddings shape:', emb.shape)

    kind = build_faiss_index(emb, outdir)
    save_docstore(docs, outdir)
    print('Index built (kind=', kind, '). Saved to', outdir)

if __name__ == '__main__':
    main()
