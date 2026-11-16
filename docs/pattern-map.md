# Creational Pattern Map

One line per creational pattern: where it genuinely fits in THIS system, or an
honest "no fit." An honest "no" is deliberate — forcing a pattern where nothing
needs it is itself a design smell.

| Pattern | Genuine fit here? |
|---|---|
| **Factory Method** | **Yes — implemented.** `ParserFactory.get_parser()` (in `data/document_parser.py`) returns the right `ResumeParser` (`PdfParser` / `DocxParser`) for a file's extension. Adding a format is one new subclass + one registry entry, with no edits to existing parsers (also fixes the old `if/elif` Open/Closed smell). |
| **Abstract Factory** | No fit. The system has no *families* of related products that must match each other. A single-product choice is Factory Method, not Abstract Factory. |
| **Builder** | No fit yet. The analysis result is a small dict; it has no complex, multi-step, many-optional-field construction that would justify a builder. Possible future fit if the result object grows. |
| **Prototype** | No fit. Nothing in the system needs to clone a pre-configured object and tweak the copy. |
| **Singleton** | No fit (intentionally). Config (API key, access token) is read from the environment in `config.py` and passed in where needed, rather than via a global singleton. This keeps dependencies explicit and testable (the Dependency Inversion habit the course teaches). |

**Chosen and implemented:** Factory Method, because it has a real motivation (per-file-type parsing) and simultaneously removes a genuine Open/Closed violation in the document parser.
