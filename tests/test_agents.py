import unittest
import os
import shutil
from agents.cv_parser import cv_details_to_markdown, extract_text_from_file, CVDetails, WorkExperience, Education
from agents.verification_agent import check_keyword_density

class TestCVParserDeterministic(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for test files if needed
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_dir, exist_ok=True)
        self.txt_file = os.path.join(self.test_dir, "test_resume.txt")
        with open(self.txt_file, "w", encoding="utf-8") as f:
            f.write("Candidate: Alice Smith\nSkills: Python, SQL")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_extract_text_from_txt_file(self):
        """Verify text extraction from simple text file."""
        extracted = extract_text_from_file(self.txt_file)
        self.assertIn("Alice Smith", extracted)
        self.assertIn("Python, SQL", extracted)

    def test_cv_details_to_markdown(self):
        """Verify formatting of CVDetails pydantic object to markdown."""
        details = CVDetails(
            full_name="Alice Smith",
            email="alice@example.com",
            phone="123-456-7890",
            location="New York, USA",
            summary="Experienced backend dev.",
            skills=["Python", "SQL", "Docker"],
            work_experience=[
                WorkExperience(
                    company="Tech Corp",
                    role="Software Engineer",
                    start_date="2021",
                    end_date="Present",
                    responsibilities=["Built REST APIs", "Optimized queries"]
                )
            ],
            education=[
                Education(
                    institution="State University",
                    degree="B.S. Computer Science",
                    graduation_year="2020"
                )
            ]
        )
        md_output = cv_details_to_markdown(details)
        self.assertIn("# Alice Smith", md_output)
        self.assertIn("alice@example.com", md_output)
        self.assertIn("## Professional Summary", md_output)
        self.assertIn("Built REST APIs", md_output)

class TestVerificationDeterministic(unittest.TestCase):
    def test_check_keyword_density_missing_terms(self):
        """Verify TF-IDF check correctly identifies missing keywords."""
        cv_text = "Experienced software engineer specializing in Python development and data storage."
        jd_text = "Seeking Python software engineer with extensive Docker, Kubernetes, and PostgreSQL experience."
        
        missing = check_keyword_density(cv_text, jd_text, top_n=12)
        # 'docker', 'kubernetes', 'postgresql' should be in the missing terms
        missing_lower = [term.lower() for term in missing]
        
        self.assertTrue(any("docker" in term for term in missing_lower), "Expected 'docker' in missing terms")
        self.assertTrue(any("kubernetes" in term for term in missing_lower), "Expected 'kubernetes' in missing terms")
        self.assertTrue(any("postgresql" in term for term in missing_lower), "Expected 'postgresql' in missing terms")

if __name__ == "__main__":
    unittest.main()
