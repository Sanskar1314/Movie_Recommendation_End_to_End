"""Reproducible user-stratified held-out rating and full-catalog ranking evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from backend.collaborative import CollaborativeModel, DEFAULT_DATA, load_dataset


def split_ratings(ratings, seed=42):
    rng = np.random.default_rng(seed)
    held_out = []
    for _, group in ratings.groupby('userId', sort=True):
        if len(group) >= 5:
            count = min(len(group) - 3, max(1, int(len(group) * 0.2)))
            held_out.extend(rng.choice(group.index.to_numpy(), count, replace=False))
    test = ratings.loc[held_out].copy()
    return ratings.drop(index=held_out).copy(), test


def evaluate(movies, ratings, seed=42, k=10):
    train, test = split_ratings(ratings, seed)
    if test.empty:
        raise ValueError('Need users with at least five ratings for evaluation.')
    model = CollaborativeModel(movies, train)
    results = {}
    examples = []
    for name, baseline in [('collaborative_with_fallback', False), ('popularity', True)]:
        errors, absolute, precision, recall, ndcg = [], [], [], [], []
        supported = 0
        for uid, group in test.groupby('userId', sort=True):
            scores, sources, _, _ = model.scores(uid)
            indices = [model.movie_index[int(mid)] for mid in group.movieId]
            predicted = model.popularity[indices] if baseline else scores[indices]
            difference = predicted - group.rating.to_numpy()
            errors.extend(difference ** 2)
            absolute.extend(abs(difference))
            if not baseline:
                supported += int((sources[indices] == 'collaborative').sum())
            relevant = set(group.loc[group.rating >= 4, 'movieId'])
            if not relevant:
                continue
            recommended = model.recommend(uid, k, baseline=baseline)['recommendations']
            hits = np.array([r['movie_id'] in relevant for r in recommended], dtype=float)
            precision.append(float(hits.sum() / k))
            recall.append(float(hits.sum() / len(relevant)))
            discount = 1 / np.log2(np.arange(len(hits)) + 2)
            ideal = sum(1 / np.log2(np.arange(min(k, len(relevant))) + 2))
            ndcg.append(float((hits * discount).sum() / ideal))
            if not baseline and len(examples) < 3:
                examples.append({'user_id': int(uid), 'movie_ids': [r['movie_id'] for r in recommended],
                                 'sources': [r['source'] for r in recommended]})
        results[name] = {'rmse': float(np.sqrt(np.mean(errors))), 'mae': float(np.mean(absolute)),
                         f'precision@{k}': float(np.mean(precision)), f'recall@{k}': float(np.mean(recall)),
                         f'ndcg@{k}': float(np.mean(ndcg)), 'ranking_users': len(precision)}
        if not baseline:
            results[name]['held_out_cf_coverage'] = supported / len(test)
    return {'dataset': 'MovieLens latest-small', 'ratings_sha256': hashlib.sha256(ratings.to_csv(index=False).encode()).hexdigest(),
            'seed': seed, 'split': 'per-user random 20%, at least 3 train ratings; not a temporal split',
            'train_ratings': len(train), 'test_ratings': len(test), 'users': ratings.userId.nunique(),
            'catalog_movies': len(movies), 'neighbors': model.neighbors, 'min_overlap': model.min_overlap,
            'similarity_shrinkage': model.shrinkage, 'minimum_candidate_support': 2,
            'ranking': 'full unseen rated-in-training catalog; relevant = held-out rating >= 4; macro averages',
            'results': results, 'personalization_examples': examples,
            'limitations': ['Single development split, not a temporal or shared research benchmark.',
                            'Missing observed relevance is not proof of dislike.',
                            'CF includes explicitly labeled popularity fallback; rating metrics cover both sources.',
                            'MovieLens is historical and self-selected; no production-quality claim.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--output', type=Path, default=Path('reports/evaluation.json'))
    args = parser.parse_args()
    movies, ratings = load_dataset(args.data_dir)
    report = evaluate(movies, ratings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
