import pytest
from main import app
from starlette.testclient import TestClient

class TestMain(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.secret_key = "MenedgerZadach"
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60


    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div class="description my-5">Ваш удобный организатор времени</div>', response.text)

    def test_registration_page(self):
        response = self.client.get('/registration')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div class="title my-5 text-center">Регистрация</div>', response.text)

    def test_authorization_page(self):
        response = self.client.get('/authorization')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div class="title my-5 text-center">Авторизация</div>', response.text)

    def test_my_tasks_page(self):
        response = self.client.get('/my_tasks')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div class="sort_text">Сортировать по:</div>', response.text)

    def test_complete_tasks_page(self):
        response = self.client.get('/complete_tasks')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div class="my-5 page_title">Завершенные</div>', response.text)
    


if __name__ == '__main__':
    unittest.main()