# Quality evaluation

Question: can an LLM still answer questions about a PDF when it only gets the generated Markdown?

## Run

1. Download the PDF from `pdf_url` into `evals/local/` and convert it with the skill.
2. Start a fresh Claude session (or subagent) that gets **only** the generated `.md` file and the questions, not the answers or the PDF.
3. Grade each answer against `a` as correct / wrong.
4. Record:
   - accuracy, overall and for `source: figure`
   - Markdown tokens: `chars / 4` (printed by convert.py)
   - approx. PDF tokens when given to Claude directly: `pages × 1,500 + text tokens` (each page is sent as an image plus its text)

Private PDFs and their questions go into `evals/local/` (gitignored), never into the repo.

## Results

| PDF | Pages | Accuracy | Figure questions | MD tokens | PDF tokens (approx.) |
|---|---|---|---|---|---|
