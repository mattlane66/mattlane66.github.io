#!/usr/bin/env python3
"""Regression checks for public-site privacy guard."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("check_privacy", Path(__file__).with_name("check_privacy.py"))
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class PrivacyTests(unittest.TestCase):
    def test_rejects_real_address_and_mailto_without_echoing_value(self):
        address = "visitor" + "@" + "private-inbox.com"
        found = privacy.issues_in_source("about/index.html", '<a href="mailto:' + address + '">Mail</a>')
        self.assertEqual(len(found), 2)
        self.assertNotIn(address, " ".join(found))

    def test_accepts_reserved_examples_and_noreply(self):
        text = ("person" + "@" + "example.com") + " " + ("1234" + "@" + "users.noreply.github.com")
        self.assertEqual(privacy.issues_in_source("README.md", text), [])

    def test_detects_mailto_even_without_email_literal(self):
        self.assertIn("mailto reference in public web file",
                      privacy.issues_in_source("index.html", "href='mailto" + ":encoded-value'"))

    def test_rejects_non_noreply_addresses(self):
        self.assertFalse(privacy.safe_source_email("person" + "@" + "inbox.net"))

    def test_does_not_reject_plain_text_mention_of_mailto_in_docs(self):
        self.assertEqual([], privacy.issues_in_source("README.md", "Never use mailto" + ": links."))


if __name__ == "__main__":
    unittest.main()
