"""Exercise real Streamlit widgets against FastAPI through its in-process client."""
import os
from pathlib import Path
import tempfile
import unittest
import requests
from unittest.mock import patch

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from backend.collaborative import DEFAULT_DATA
from backend.main import app


@unittest.skipUnless((DEFAULT_DATA / 'ratings.csv').exists(), 'Download MovieLens to run real-data UI integration')
class UserJourneyTests(unittest.TestCase):
    def test_connection_error_can_be_retried(self):
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"users": []}'
        with patch('requests.request', side_effect=requests.ConnectionError('Connection refused')) as request:
            ui = AppTest.from_file('frontend/app.py', default_timeout=30).run()
            self.assertFalse(ui.exception)
            self.assertIn('Cannot connect', ui.error[0].value)
            request.side_effect = None
            request.return_value = response
            next(b for b in ui.button if b.label == 'Retry connection').click().run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.error)
            self.assertTrue(any('Create a profile' in message.value for message in ui.info))

    def test_create_rate_refresh_switch_and_legacy_browse(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'RATINGS_DB': str(Path(directory) / 'ui.sqlite3'), 'TMDB_API_KEY': ''
        }), TestClient(app) as client:
            def api_request(method, url, **kwargs):
                path = '/' + url.split('/', 3)[3]
                kwargs.pop('timeout', None)
                response = client.request(method, path, **kwargs)
                response.ok = response.status_code < 400
                return response

            with patch('requests.request', side_effect=api_request), patch('requests.get', side_effect=lambda url, **kw: api_request('GET', url, **kw)), patch('requests.post', side_effect=lambda url, **kw: api_request('POST', url, **kw)):
                ui = AppTest.from_file('frontend/app.py', default_timeout=30).run()
                self.assertFalse(ui.exception)
                ui.text_input[0].set_value('UI Viewer')
                ui.button[0].click().run()
                self.assertFalse(ui.exception)
                self.assertEqual(len(client.get('/personal/users').json()['users']), 1)
                ui.slider[0].set_value(4.5)
                next(b for b in ui.button if b.label == 'Save rating').click().run()
                self.assertFalse(ui.exception)
                self.assertEqual(client.get('/personal/users/1/ratings').json()['ratings'][0]['rating'], 4.5)
                next(b for b in ui.button if b.label == 'Refresh recommendations').click().run()
                self.assertFalse(ui.exception)
                ui.text_input[0].set_value('Another viewer')
                next(b for b in ui.button if b.label == 'Create profile').click().run()
                self.assertFalse(ui.exception)
                self.assertEqual(ui.selectbox[0].value, 2)
                ui.selectbox[0].set_value(1).run()
                self.assertFalse(ui.exception)
                self.assertEqual(ui.selectbox[0].value, 1)
                if client.get('/health').json()['legacy_ready']:
                    ui.radio[0].set_value('Browse Movies').run()
                    self.assertFalse(ui.exception)
                    self.assertTrue(any('Popular Movies' in x.value for x in ui.markdown))
                    ui.query_params['page'] = 'detail'
                    ui.query_params['movie'] = 'Toy Story'
                    ui.run()
                    self.assertFalse(ui.exception)
                    self.assertTrue(any('More Like This' in x.value for x in ui.markdown))


if __name__ == '__main__':
    unittest.main()
