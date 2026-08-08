import unittest
from unittest.mock import patch, MagicMock
import json
from tools import query_local_perplexity


class TestQueryLocalPerplexity(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_query_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"text": "Perplexity query answer"}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = query_local_perplexity.query_local_perplexity.invoke({"query": "What is AgentK?"})
        self.assertEqual(res, "Perplexity query answer")

    @patch("urllib.request.urlopen")
    def test_query_error_handling(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")

        res = query_local_perplexity.query_local_perplexity.invoke({"query": "Test query"})
        self.assertIn("Execution Fault: Connection refused", res)


if __name__ == "__main__":
    unittest.main()
