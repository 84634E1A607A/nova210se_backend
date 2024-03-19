from django.test import TestCase
from django.urls import reverse

from main.tests.utils import JsonClient


class MiddleWareTests(TestCase):
    def setUp(self):
        self.client = JsonClient()

    def test_bad_json(self):
        """
        Test a bad JSON request
        """

        response = self.client.post(reverse("user_register"), "{This is not JSON}")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_bad_content_type(self):
        """
        Test a bad content type
        """

        response = self.client.post(reverse("user_register"), "password=", content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_404_page(self):
        """
        Test the 404 page
        """

        response = self.client.get("/this_page_does_not_exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        data = response.json()
        self.assertFalse(data["ok"])

    def test_http_options(self):
        """
        Test the OPTIONS request
        """

        response = self.client.options(reverse("user_register"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Allow"], "POST, OPTIONS")

    def test_http_method_not_allowed(self):
        """
        Test a not allowed method
        """

        response = self.client.delete(reverse("user_register"))
        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertFalse(data["ok"])
