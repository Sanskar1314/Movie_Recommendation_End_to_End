"""Fetch the official small development dataset, preserving its usage license."""
import argparse
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile

URL = 'https://files.grouplens.org/datasets/movielens/ml-latest-small.zip'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data'))
    args = parser.parse_args()
    with urllib.request.urlopen(URL, timeout=60) as response:
        payload = response.read()
    destination = args.output / 'ml-latest-small'
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in ('README.txt', 'movies.csv', 'ratings.csv', 'links.csv', 'tags.csv'):
            (destination / name).write_bytes(archive.read('ml-latest-small/' + name))
    digest = hashlib.sha256(payload).hexdigest()
    (destination / 'SOURCE.txt').write_text(f'{URL}\nArchive SHA256: {digest}\n')
    print(f'Downloaded to {destination}; SHA256 {digest}')
    print('Read README.txt for research use, attribution and commercial-use restrictions.')


if __name__ == '__main__':
    main()
