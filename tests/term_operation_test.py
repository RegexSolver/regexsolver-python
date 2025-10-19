import json
import requests_mock
import unittest

from regexsolver import ApiError, RegexSolver, Term


class TermsOperationTest(unittest.TestCase):
    def setUp(self):
        RegexSolver.initialize("TOKEN")

    def test_error_response(self):
        with open('tests/assets/response_error.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/intersection",
                json=json_response, status_code=400
            )

            term1 = Term.regex(r"abc")
            term2 = Term.regex(r"de")

            try:
                term1.intersection(term2)
            except ApiError as err:
                self.assertEqual(
                    "The API returned the following error: A random error.",
                    err.args[0]
                )


if __name__ == '__main__':
    unittest.main()
