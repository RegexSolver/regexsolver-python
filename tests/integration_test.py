import unittest
from dotenv import load_dotenv
from regexsolver import RegexSolver, ResponseFormat, Term


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        load_dotenv()
        RegexSolver.initialize()
    
    # Analyze
    
    def test_analyze_cardinality(self):
        term = Term.regex(r"[0-4]")
        cardinality = term.get_cardinality()

        self.assertEqual(
            "Integer(5)",
            str(cardinality)
        )
            
    def test_analyze_dot(self):
        term = Term.regex(r"(abc|de)")
        dot = term.get_dot()

        self.assertTrue(dot.startswith("digraph "))
            
    def test_analyze_empty_string(self):
        term = Term.regex(r"")

        result = term.is_empty_string()

        self.assertTrue(result)
    
    def test_analyze_empty(self):
        term = Term.regex(r"[]")

        result = term.is_empty()

        self.assertTrue(result)
            
    def test_analyze_total(self):
        term = Term.regex(r".*")

        result = term.is_total()

        self.assertTrue(result)
            
    def test_analyze_equivalent(self):
        term1 = Term.regex(r"(abc|de)")
        term2 = Term.fair("<uw$8AJYkaU].HFn1kT[tx*-VAZ8usSKXcEKZ[wx:F8vYuR-b?tFFk1eM2RXs9yuu5dakz7r/{!AW9/(hK0]knHS&Q]!@K=ahmGr1Dbjb5(XE1UT%Ab@8rXvYop}$")

        result = term1.equivalent(term2)

        self.assertFalse(result)
    
    def test_analyze_length_empty(self):
        term = Term.regex(r"[]")
        length = term.get_length()

        self.assertEqual(
            "Length[minimum=None, maximum=None]",
            str(length)
        )
      
    def test_analyze_length(self):
        term = Term.regex(r"(abc)?")
        length = term.get_length()

        self.assertEqual(
            "Length[minimum=0, maximum=3]",
            str(length)
        )
            
    def test_analyze_pattern(self):
        term = Term.regex(r"abc.*")
        pattern = term.get_pattern()

        self.assertEqual(
            "abc.*",
            pattern
        )

    def test_analyze_subset(self):
        term1 = Term.regex(r"de")
        term2 = Term.regex(r"(abc|de)")

        result = term1.subset(term2)

        self.assertTrue(result)
    
    # Compute
    
    def test_compute_concat(self):
        term1 = Term.regex(r"abc")
        term2 = Term.regex(r"de")

        result = term1.concat(term2, response_format=ResponseFormat.REGEX)

        self.assertEqual("regex=abcde", str(result))
    
    def test_compute_difference(self):
        term1 = Term.regex(r"(abc|de)")
        term2 = Term.regex(r"de")

        result = term1.difference(term2, response_format=ResponseFormat.REGEX)

        self.assertEqual("regex=abc", str(result))
    
    def test_compute_intersection(self):
        term1 = Term.regex(r"(abc|de){2}")
        term2 = Term.regex(r"de.*")
        term3 = Term.regex(r".*abc")

        result = term1.intersection(term2, term3, response_format=ResponseFormat.REGEX)

        self.assertEqual("regex=deabc", str(result))
            
    def test_compute_repeat(self):
        term = Term.regex(r"abc")

        result = term.repeat(3, 5, response_format=ResponseFormat.REGEX)

        self.assertEqual("regex=(abc){3,5}", str(result))

    def test_compute_union(self):
        term1 = Term.regex(r"abc")
        term2 = Term.regex(r"de")
        term3 = Term.regex(r"fghi")

        result = term1.union(term2, term3, response_format=ResponseFormat.REGEX)

        self.assertEqual("regex=(abc|de|fghi)", str(result))
    
    # Generate
            
    def test_generate_strings(self):
        term = Term.regex(r"(abc|de){2}")
        strings = term.generate_strings(10)

        self.assertEqual(4, len(strings))
        
    # README
    
    def test_readme_quickstart(self):
        term1 = Term.regex(r"(abc|de|fg){2,}")
        term2 = Term.regex(r"de.*")
        term3 = Term.regex(r".*abc")

        result = term1.intersection(term2, term3).difference(
            Term.regex(r".+(abc|de).+")
        )

        self.assertEqual(r"de(fg)*abc", result.get_pattern())
        
    def test_readme_response_format(self):
        term = Term.regex(r"abcde")
        result = term.union(Term.regex(r"de"), response_format=ResponseFormat.REGEX)
        self.assertEqual("regex=(abc)?de", str(result))

        result = term.intersection(Term.regex(r"de.*"), response_format=ResponseFormat.FAIR)
        self.assertTrue(str(result).startswith("fair="))
        
    def test_readme_response_format(self):
        term = Term.regex(r"abcde")
        result = term.union(Term.regex(r"de"), response_format=ResponseFormat.REGEX)
        self.assertEqual("regex=(abc)?de", str(result))

        result = term.intersection(Term.regex(r"de.*"), response_format=ResponseFormat.FAIR)
        self.assertTrue(str(result).startswith("fair="))
            
if __name__ == '__main__':
    unittest.main()
