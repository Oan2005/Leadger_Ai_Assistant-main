import os
import unittest


@unittest.skipUnless(
    os.getenv("RUN_EXTERNAL_INTEGRATION_TESTS") == "1",
    "Set RUN_EXTERNAL_INTEGRATION_TESTS=1 only for an isolated staging environment.",
)
class ExternalFlowTests(unittest.TestCase):
    """Destructive integration tests require explicitly approved staging credentials."""

    @unittest.skip("Implement against approved staging fixtures before enabling.")
    def test_authentication_and_authorization(self):
        pass

    @unittest.skip("Implement against approved staging fixtures before enabling.")
    def test_invitation_lifecycle(self):
        pass

    @unittest.skip("Implement against approved staging fixtures before enabling.")
    def test_document_lifecycle(self):
        pass

    @unittest.skip("Implement against approved staging fixtures before enabling.")
    def test_employee_question_and_analytics(self):
        pass
