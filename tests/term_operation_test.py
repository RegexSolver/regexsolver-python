import json
import requests_mock
import unittest

from regexsolver import ApiError, RegexSolver, ResponseFormat, Term


class TermsOperationTest(unittest.TestCase):
    def setUp(self):
        RegexSolver.initialize("TOKEN")
        
    def test_analyze_cardinality(self):
        with open('tests/assets/response_analyze_cardinality.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/cardinality",
                json=json_response, status_code=200
            )

            term = Term.regex(r"[0-4]")
            cardinality = term.get_cardinality()

            self.assertEqual(
                "Integer(5)",
                str(cardinality)
            )

    def test_analyze_details(self):
        with open('tests/assets/response_analyze_details.json') as response:
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

    def test_analyze_details_infinite(self):
        with open('tests/assets/response_analyze_details_infinite.json') as response:
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
    
    def test_analyze_details_empty(self):
        with open('tests/assets/response_analyze_details_empty.json') as response:
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
            
    def test_analyze_empty_string(self):
        with open('tests/assets/response_analyze_empty_string.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/empty_string",
                json=json_response, status_code=200
            )

            term = Term.regex(r"")

            result = term.is_empty_string()

            self.assertEqual(True, result)
    
    def test_analyze_empty(self):
        with open('tests/assets/response_analyze_empty.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/empty",
                json=json_response, status_code=200
            )

            term = Term.regex(r"[]")

            result = term.is_empty()

            self.assertEqual(True, result)
            
    def test_analyze_total(self):
        with open('tests/assets/response_analyze_total.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/total",
                json=json_response, status_code=200
            )

            term = Term.regex(r"abc")

            result = term.is_total()

            self.assertEqual(False, result)
            
    def test_analyze_equivalent(self):
        with open('tests/assets/response_analyze_equivalent.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/equivalent",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"(abc|de)")
            term2 = Term.fair(
                "rgmsW[1g2LvP=Gr&V>sLc#w-!No&(oq@Sf>X).?lI3{uh{80qWEH[#0.pHq@B-9o[LpP-a#fYI+")

            result = term1.equivalent(term2)

            self.assertEqual(False, result)
    
    def test_analyze_length_empty(self):
        with open('tests/assets/response_analyze_length_empty.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/length",
                json=json_response, status_code=200
            )

            term = Term.regex(r"[]")
            length = term.get_length()

            self.assertEqual(
                "Length[minimum=None, maximum=None]",
                str(length)
            )
      
    def test_analyze_length(self):
        with open('tests/assets/response_analyze_length.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/length",
                json=json_response, status_code=200
            )

            term = Term.regex(r"(abc)?")
            length = term.get_length()

            self.assertEqual(
                "Length[minimum=0, maximum=3]",
                str(length)
            )

    def test_analyze_subset(self):
        with open('tests/assets/response_analyze_subset.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/analyze/subset",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"de")
            term2 = Term.regex(r"(abc|de)")

            result = term1.subset(term2)

            self.assertEqual(True, result)
    
    def test_compute_concat(self):
        with open('tests/assets/response_compute_concat.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/concat",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"abc")
            term2 = Term.regex(r"de")

            result = term1.concat(term2, response_format=ResponseFormat.REGEX)

            self.assertEqual("regex=abcde", str(result))
    
    def test_compute_difference(self):
        with open('tests/assets/response_compute_difference.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/difference",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"(abc|de)")
            term2 = Term.regex(r"de")

            result = term1.difference(term2, response_format=ResponseFormat.REGEX)

            self.assertEqual("regex=abc", str(result))
    
    def test_compute_intersection(self):
        with open('tests/assets/response_compute_intersection.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/intersection",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"(abc|de){2}")
            term2 = Term.regex(r"de.*")
            term3 = Term.regex(r".*abc")

            result = term1.intersection(term2, term3, response_format=ResponseFormat.REGEX)

            self.assertEqual("regex=deabc", str(result))

    def test_compute_union(self):
        with open('tests/assets/response_compute_union.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/compute/union",
                json=json_response, status_code=200
            )

            term1 = Term.regex(r"abc")
            term2 = Term.regex(r"de")
            term3 = Term.regex(r"fghi")

            result = term1.union(term2, term3, response_format=ResponseFormat.REGEX)

            self.assertEqual("regex=(abc|de|fghi)", str(result))
            
    def test_generate_strings(self):
        with open('tests/assets/response_generate_strings.json') as response:
            json_response = json.load(response)
        with requests_mock.Mocker() as mock:
            mock.post(
                "https://api.regexsolver.com/api/generate/strings",
                json=json_response, status_code=200
            )

            term = Term.regex(r"(abc|de){2}")
            strings = term.generate_strings(10)

            self.assertEqual(4, len(strings))

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
