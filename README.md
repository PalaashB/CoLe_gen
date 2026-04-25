# AI Cover Letter Generator

Generate hyper-personalised cover letters by combining deep company research with your resume data. Powered by NVIDIA's Nemotron 120B model via the NIM API — every letter reads like you spent 45 minutes researching the company.

---

## Features

- **URL or Text Input** — Paste a job URL (LinkedIn, Indeed, Lever, Greenhouse, any site) or raw job description text
- **AI Job Parsing** — Automatically extracts company, position, skills, tech stack, and more
- **Deep Company Research** — Scrapes company website, searches recent news, analyses tech stack and culture
- **Personalised Generation** — Matches your experience to the company's specific needs with real metrics
- **Quality Scoring** — Evaluates every letter on 6 dimensions (company references, metrics, tech match, culture fit, length, originality)
- **PDF Export** — Professional typeset cover letters ready to send
- **Application Tracker** — Logs every application with date, company, score, and PDF path
- **24h Research Cache** — Don't re-research the same company within a day
- **Streaming Output** — Watch the letter being written in real time

---

## Prerequisites

- **Python 3.10+**
- **Internet connection** (for API calls and web research)
- **NVIDIA NIM API key** (free at [build.nvidia.com](https://build.nvidia.com))

---

## Installation

```bash
# 1. Clone / navigate to the project
cd cl_gen

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser
playwright install chromium

# 5. Set up environment
cp .env.example .env
# Edit .env and add your NVIDIA API key

# 6. Customise your profile
# Edit config/user_profile.json with your real info

# 7. Run!
python main.py
```

---

## Getting Your API Key

1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Create a free account
3. Navigate to the Nemotron model
4. Generate an API key (starts with `nvapi-`)
5. Paste it into your `.env` file

---

## Usage

### With a Job URL

```
Choose option: 1

Paste job posting URL or description below.
(Press Enter twice on an empty line when done, or Ctrl+D)

> https://jobs.lever.co/stripe/senior-backend-engineer
>

Detecting input type... URL detected
Scraping job page... done
Parsing job details with AI... done

--- Extracted Job Details ---
Company:      Stripe
Position:     Senior Backend Engineer
...
```

### With Pasted Text

```
Choose option: 1

Paste job posting URL or description below.

> Senior Software Engineer at Notion
> Remote - US
> Requirements: Python, React, PostgreSQL, 3+ years
> We're looking for someone who loves building tools
> that make teams more productive.
>

Detecting input type... Text input detected
Parsing job details with AI... done
```

### Generated Output

The tool will:
1. Extract structured job data and confirm with you
2. Research the company (website, news, tech stack, culture)
3. Generate a streaming cover letter personalised with research insights
4. Score the letter on quality dimensions
5. Offer to export as PDF, regenerate, or edit

---

## Configuration

### User Profile (`config/user_profile.json`)

Edit this file with your real information:
- Personal details (name, email, phone, links)
- Work experience with specific achievements and metrics
- Skills (languages, frameworks, tools)
- Education and certifications
- Job preferences

The more specific your achievements (with numbers!), the better your cover letters will be.

### Settings

- **Model**: `nvidia/nemotron-3-super-120b-a12b` (configurable in `config/settings.py`)
- **Temperatures**: 0.1 for extraction, 0.4 for synthesis, 0.7 for generation
- **Cache**: Research cached 24h, clearable from Settings menu

### Optional: SerpAPI

For better web search results, add a [SerpAPI](https://serpapi.com) key to your `.env`:
```
SERPAPI_KEY=your-serpapi-key
```
Without it, the tool falls back to DuckDuckGo HTML search (no API key needed).

---

## Project Structure

```
cl_gen/
├── main.py                    # CLI entry point and menu
├── requirements.txt           # Dependencies
├── .env.example               # Environment template
├── config/
│   ├── settings.py            # App constants and model config
│   └── user_profile.json      # Your resume data
├── core/
│   ├── job_parser.py          # URL/text detection, structured extraction
│   ├── research_agent.py      # Deep company research engine
│   ├── letter_generator.py    # Cover letter generation + quality scoring
│   └── pdf_generator.py       # Professional PDF creation
├── utils/
│   ├── nvidia_client.py       # NVIDIA API wrapper (all LLM calls)
│   ├── scraper.py             # Playwright + BeautifulSoup scraping
│   ├── cache.py               # Disk-based JSON cache with TTL
│   └── helpers.py             # Display, input, and formatting
├── data/
│   ├── applications/          # Generated PDFs
│   ├── cache/                 # Research cache
│   └── applications_log.json  # Application tracker
└── tests/
    ├── test_parser.py         # URL detection tests
    ├── test_nvidia.py         # API connectivity tests
    └── test_quality.py        # Quality scoring tests
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `NVIDIA API key not found` | Add `NVIDIA_API_KEY=nvapi-...` to `.env` |
| `Invalid NVIDIA API key` | Regenerate at [build.nvidia.com](https://build.nvidia.com) |
| `Rate limited` | Wait a moment — the tool auto-retries with backoff |
| `Page requires authentication` | Paste the job text directly instead of URL |
| `Playwright not installed` | Run `playwright install chromium` |
| `Research limited` | Add a `SERPAPI_KEY` for better search results |
| `PDF permission denied` | Check write permissions on `data/applications/` |

---

## Running Tests

```bash
# All tests (parser + quality, skips API tests without key)
python -m pytest tests/ -v

# Just parser tests
python -m pytest tests/test_parser.py -v

# Just quality tests
python -m pytest tests/test_quality.py -v

# API tests (requires valid NVIDIA_API_KEY in .env)
python -m pytest tests/test_nvidia.py -v
```

---

## License

MIT
