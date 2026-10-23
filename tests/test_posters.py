import unittest
from unittest.mock import patch

import requests

from frontend import posters


def response(status, content=b'', content_type='image/jpeg', payload=None):
    result = requests.Response()
    result.status_code = status
    result._content = content
    result.headers['Content-Type'] = content_type
    if payload is not None:
        result.json = lambda: payload
    return result


class PosterTests(unittest.TestCase):
    def setUp(self):
        posters.image_source.clear()
        posters.tmdb_poster_path.clear()

    def test_local_image_does_not_require_api_key(self):
        with patch.object(posters, 'local_posters', return_value={'movie': (12, '/local.jpg')}), patch('requests.get', return_value=response(200, b'jpeg')) as get:
            self.assertTrue(posters.poster_source('Movie').startswith('data:image/jpeg;base64,'))
            self.assertEqual(get.call_count, 1)
            self.assertNotIn('api_key', get.call_args.kwargs)

    def test_stale_image_recovers_by_exact_tmdb_id(self):
        with patch.object(posters, 'api_key', return_value='test-key'), patch('requests.get', side_effect=[
            response(404), response(200, payload={'poster_path': '/updated.jpg'}), response(200, b'jpeg')
        ]) as get:
            result = posters.poster_source('Different movie with same title', 123, 'https://image.tmdb.org/t/p/w500/old.jpg')
            self.assertTrue(result.startswith('data:image/jpeg;base64,'))
            self.assertEqual(get.call_args_list[1].args[0], 'https://api.themoviedb.org/3/movie/123')

    def test_missing_image_without_key_is_cleanly_unavailable(self):
        with patch.object(posters, 'api_key', return_value=''), patch.object(posters, 'local_posters', return_value={}):
            self.assertIsNone(posters.poster_source('Unknown'))

    def test_timeout_and_invalid_content_do_not_make_broken_images(self):
        with patch('requests.get', side_effect=requests.Timeout()):
            self.assertIsNone(posters.image_source('/timeout.jpg'))
        with patch('requests.get', return_value=response(200, b'error page', 'text/html')):
            self.assertIsNone(posters.image_source('/bad.jpg'))

    def test_search_checks_title_and_year(self):
        with patch('requests.get', return_value=response(200, payload={'results': [
            {'title': 'Movie', 'release_date': '2020-01-01', 'poster_path': '/wrong.jpg'},
            {'title': 'Movie', 'release_date': '1990-01-01', 'poster_path': '/correct.jpg'}
        ]})):
            self.assertEqual(posters.tmdb_poster_path('Movie (1990)', None, 'test-key'), '/correct.jpg')


if __name__ == '__main__':
    unittest.main()
