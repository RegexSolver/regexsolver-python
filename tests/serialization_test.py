import unittest

from regexsolver import GenerateStringsRequest, MultiTermsRequest, Term


class SerializationTest(unittest.TestCase):
    def test_serialize_term(self):
        self.assert_serialization(Term.regex(r".*"))
        self.assert_serialization(Term.regex(r""))

        self.assert_serialization(Term.fair(
            "rgmsW[1g2LvP=Gr&V>sLc#w-!No&(opHq@B-9o[LpP-a#fYI+"
        ))
        self.assert_serialization(Term.fair("=rgmsW[1g2LvP=Gr&+"))
        self.assert_serialization(Term.fair(""))

    def assert_serialization(self, term: Term):
        serialized = term.serialize()
        deserialized = Term.deserialize(serialized)

        self.assertEqual(term, deserialized)

    def test_serialize_requests(self):
        request = MultiTermsRequest(
            terms=[Term.regex(r"abc"), Term.regex(r"def"), Term.regex(r"ghi")])
        self.assertEqual(
            {
                "terms": [
                    {"type": "regex", "value": "abc"},
                    {"type": "regex", "value": "def"},
                    {"type": "regex", "value": "ghi"}
                ]
            },
            request.model_dump()
        )

        request = GenerateStringsRequest(
            term=Term.regex(r"(abc|de){2,3}"), count=10)
        self.assertEqual(
            {
                "term": {"type": "regex", "value": "(abc|de){2,3}"},
                "count": 10
            },
            request.model_dump()
        )

        request = Term.regex(r"(abc|de){2,3}")
        self.assertEqual(
            {"type": "regex", "value": "(abc|de){2,3}"},
            request.model_dump()
        )


if __name__ == '__main__':
    unittest.main()
