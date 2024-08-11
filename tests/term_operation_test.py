import json
import requests_mock
import unittest

from regexsolver import ApiError, RegexSolver, Term


class TermsOperationTest(unittest.TestCase):
    def setUp(self):
        RegexSolver.get_instance().initialize("TOKEN")

    def test_get_details(self):
        with open('tests/assets/response_getDetails.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/details",
                json=json_response, status_code=200
            )

            term = Term.regex(r"(abc|de)")
            details = term.get_details()

            self.assertEqual(
                "Details[cardinality=Integer(2), length=Length[minimum=2, maximum=3], empty=False, total=False]",
                str(details)
            )

    def test_get_details_infinite(self):
        with open('tests/assets/response_getDetails_infinite.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/details",
                json=json_response, status_code=200
            )

            term = Term.regex(r".*")
            details = term.get_details()

            self.assertEqual(
                "Details[cardinality=Infinite, length=Length[minimum=0, maximum=None], empty=False, total=True]",
                str(details)
            )
    
    def test_get_details_empty(self):
        with open('tests/assets/response_getDetails_empty.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/details",
                json=json_response, status_code=200
            )

            term = Term.regex(r"a.")
            details = term.get_details()

            self.assertEqual(
                "Details[cardinality=Integer(0), length=Length[minimum=None, maximum=None], empty=True, total=False]",
                str(details)
            )

    def test_generate_strings(self):
        with open('tests/assets/response_generateStrings.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/generate/strings",
                json=json_response, status_code=200
            )

            term = Term.regex(r"(abc|de){2}")
            strings = term.generate_strings(10)

            self.assertEqual(4, len(strings))

    def test_intersection(self):
        with open('tests/assets/response_intersection.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/intersection",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"(abc|de){2}")
            term2 = Term.regex(r"de.*")
            term3 = Term.regex(r".*abc")

            result = term1.intersection(term2, term3)

            self.assertEqual("regex=deabc", str(result))

    def test_union(self):
        with open('tests/assets/response_union.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/union",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"abc")
            term2 = Term.regex(r"de")
            term3 = Term.regex(r"fghi")

            result = term1.union(term2, term3)

            self.assertEqual("regex=(abc|de|fghi)", str(result))

    def test_subtraction(self):
        with open('tests/assets/response_subtraction.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/subtraction",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"(abc|de)")
            term2 = Term.regex(r"de")

            result = term1.subtraction(term2)

            self.assertEqual("regex=abc", str(result))

    def test_is_equivalent_to(self):
        with open('tests/assets/response_isEquivalentTo.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/equivalence",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"(abc|de)")
            term2 = Term.fair(
                "rgmsW[1g2LvP=Gr&V>sLc#w-!No&(oq@Sf>X).?lI3{uh{80qWEH[#0.pHq@B-9o[LpP-a#fYI+")

            result = term1.is_equivalent_to(term2)

            self.assertEqual(False, result)

    def test_is_subset_of(self):
        with open('tests/assets/response_isSubsetOf.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/subset",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"de")
            term2 = Term.regex(r"(abc|de)")

            result = term1.is_subset_of(term2)

            self.assertEqual(True, result)

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
