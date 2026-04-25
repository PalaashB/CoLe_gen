import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import NVIDIA_MODEL
from core.job_parser import JobParser
from core.research_agent import CompanyResearchAgent
from core.letter_generator import CoverLetterGenerator
from core.pdf_generator import PDFGenerator
from utils.nvidia_client import NvidiaLLM
from utils.scraper import WebScraper
from utils.cache import DiskCache

def main():
    print("Testing End-to-End flow programmatically...")
    
    llm = NvidiaLLM()
    scraper = WebScraper()
    cache = DiskCache()
    parser = JobParser(llm, scraper)
    researcher = CompanyResearchAgent(llm, scraper, cache)
    generator = CoverLetterGenerator(llm)
    pdf_gen = PDFGenerator()

    # Load default profile
    with open("config/user_profile.json", "r") as f:
        profile = json.load(f)

    # 1. Parse Job
    print("\n--- 1. PARSING JOB ---")
    raw_input = "Software Engineer at OpenAI. Remote. We are looking for python and generative AI skills. 3+ years experience."
    # Since parser asks for confirmation if missing company_name from stdin, we simulate via llm direct call
    job_data = parser._extract_structured_data(raw_input)
    print("Extracted Job:", json.dumps(job_data, indent=2))
    
    # Override missing fields if any
    if not job_data.get("company_name"):
        job_data["company_name"] = "OpenAI"
    if not job_data.get("position_title"):
        job_data["position_title"] = "Software Engineer"
        
    # 2. Research
    print("\n--- 2. RESEARCHING ---")
    research = researcher.research_company(job_data)
    print("Research Complete.")
    
    # 3. Generate
    print("\n--- 3. GENERATING ---")
    result = generator.generate(profile, job_data, research)
    letter = result["letter"]
    quality = result["quality"]
    print(f"\nScore: {quality['score']}")
    
    # 4. Generate PDF
    print("\n--- 4. GENERATING PDF ---")
    pdf_path = pdf_gen.generate(letter, profile, job_data)
    print(f"PDF saved to: {pdf_path}")
    
    scraper.close()
    print("\nSuccess.")

if __name__ == "__main__":
    main()
