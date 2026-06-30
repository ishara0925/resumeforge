import unittest
import os
import shutil
from agents.cv_parser import (
    cv_details_to_markdown,
    extract_text_from_file,
    CVDetails,
    WorkExperience,
    Education,
    get_parsed_cv_path,
    list_parsed_cv_files,
    parse_cv_to_markdown
)
from agents.verification_agent import check_keyword_density
from agents.jd_parser import (
    read_jd_links,
    scrape_url,
    process_jds_step1_scrape,
    check_for_scraping_failures
)

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

class TestCVParserCaching(unittest.TestCase):
    def setUp(self):
        self.test_input_dir = os.path.join("data", "input")
        self.created_input_dir = False
        if not os.path.exists(self.test_input_dir):
            os.makedirs(self.test_input_dir, exist_ok=True)
            self.created_input_dir = True
            
        self.temp_cv_name = "test_caching_resume"
        self.temp_cv_file = f"{self.temp_cv_name}.pdf"
        self.expected_md_file = os.path.join(self.test_input_dir, f"{self.temp_cv_name}_parsed.md")
        
        # Write dummy cached file
        with open(self.expected_md_file, "w", encoding="utf-8") as f:
            f.write("# Cached CV Content\nSkills: Caching, Testing")

    def tearDown(self):
        if os.path.exists(self.expected_md_file):
            os.remove(self.expected_md_file)
        if self.created_input_dir and os.path.exists(self.test_input_dir):
            try:
                # Only remove if it's empty
                if not os.listdir(self.test_input_dir):
                    os.rmdir(self.test_input_dir)
            except Exception:
                pass

    def test_get_parsed_cv_path(self):
        path = get_parsed_cv_path(self.temp_cv_file)
        self.assertEqual(os.path.normpath(path), os.path.normpath(self.expected_md_file))

    def test_list_parsed_cv_files(self):
        files = list_parsed_cv_files(self.test_input_dir)
        self.assertIn(f"{self.temp_cv_name}_parsed.md", files)

    def test_parse_cv_to_markdown_uses_cache(self):
        content = parse_cv_to_markdown(self.temp_cv_file)
        self.assertEqual(content, "# Cached CV Content\nSkills: Caching, Testing")

class TestJDParserBatch(unittest.TestCase):
    def setUp(self):
        self.input_dir = os.path.join("data", "input")
        self.links_file = os.path.join(self.input_dir, "jd_links.md")
        
        # Backup existing jd_links.md if it exists
        self.backup_links = None
        if os.path.exists(self.links_file):
            with open(self.links_file, "r", encoding="utf-8") as f:
                self.backup_links = f.read()
                
        # Write test URLs to jd_links.md
        os.makedirs(self.input_dir, exist_ok=True)
        with open(self.links_file, "w", encoding="utf-8") as f:
            f.write("https://httpbin.org/status/200\nhttps://httpbin.org/status/404\n")

    def tearDown(self):
        # Restore backup or remove links_file
        if self.backup_links is not None:
            with open(self.links_file, "w", encoding="utf-8") as f:
                f.write(self.backup_links)
        else:
            if os.path.exists(self.links_file):
                os.remove(self.links_file)
                
        # Clean up any jd_raw files created by the test
        if os.path.exists(self.input_dir):
            for file in os.listdir(self.input_dir):
                if file.startswith("jd_raw_") and file.endswith(".md"):
                    try:
                        os.remove(os.path.join(self.input_dir, file))
                    except Exception:
                        pass

    def test_read_jd_links(self):
        links = read_jd_links(self.links_file)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0], "https://httpbin.org/status/200")
        self.assertEqual(links[1], "https://httpbin.org/status/404")

    def test_check_for_scraping_failures(self):
        results = [
            {"index": 1, "raw_path": os.path.join(self.input_dir, "jd_raw_1.md")},
            {"index": 2, "raw_path": os.path.join(self.input_dir, "jd_raw_2.md")}
        ]
        # Create one non-empty and one empty file
        with open(results[0]["raw_path"], "w", encoding="utf-8") as f:
            f.write("Some job description text")
        with open(results[1]["raw_path"], "w", encoding="utf-8") as f:
            f.write("") # empty file represents failure
            
        failures = check_for_scraping_failures(results)
        self.assertEqual(failures, [2])

if __name__ == "__main__":
    unittest.main()
