# """
# llm_cleaner.py - LLM-Based TTS Text Normalization
# ==================================================
# Location : MODAL/llm_cleaner.py

# Uses Azure OpenAI via LangChain LCEL to normalize raw text
# before passing it to the XTTS-v2 TTS model.
# """

# import os
# from dotenv import load_dotenv
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_openai import AzureChatOpenAI

# # ---------------------------------------------------------------------------
# # Load .env
# # ---------------------------------------------------------------------------
# load_dotenv()

# AZURE_API_KEY       = os.getenv("AZURE_OPENAI_API_KEY", "")
# AZURE_ENDPOINT      = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
# AZURE_DEPLOYMENT    = os.getenv("AZURE_OPENAI_MODEL_NAME", "")   # matches your .env
# AZURE_API_VERSION   = os.getenv("AZURE_OPENAI_API_VERSION", "")

# # ---------------------------------------------------------------------------
# # System prompt
# # ---------------------------------------------------------------------------
# _SYSTEM_PROMPT = """\
# You are a strict TTS Text Normalization Node. Your ONLY function is to convert \
# raw input text into clean, naturally speakable output for a Text-To-Speech engine.

# Process the input in this EXACT order. Apply every rule before moving to the next.

# RULE 1 - ACRONYMS AND INITIALISMS:
# Identify sequences of 2 or more consecutive UPPERCASE letters that form an \
# acronym or initialism. Separate each letter with a single space.
#   API    becomes  A P I
#   UCP    becomes  U C P
#   GFPGAN becomes  G F P G A N
#   AI     becomes  A I
#   FYP    becomes  F Y P
# Exception: Do NOT split mixed-case words like Pakistan or Google.
# Only apply to ALL-CAPS sequences of 2 or more letters.

# RULE 2 - EMOJIS AND UNICODE ICONS:
# Completely remove ALL emojis, emoticons, and unicode icon characters.
# Do NOT replace them with words or descriptions. Just delete them entirely.
#   Great job! See you
#   Score: 100

# RULE 3 - DASHES AND HYPHENS:
# Remove ALL dash and hyphen characters and replace each one with a single space \
# so that words never merge together.
# Applies to hyphen, en dash, em dash, and any similar dash character.
#   state-of-the-art  becomes  state of the art
#   2024-2025         becomes  2024 2025
#   real-time         becomes  real time

# RULE 4 - EMAILS:
# Detect full email addresses and convert each to spoken form.
#   Replace @ with  at
#   Replace each dot in the domain with  dot
#   ali@test.com         becomes  ali at test dot com
#   contact@fyp.edu.pk   becomes  contact at fyp dot edu dot pk

# RULE 5 - URLS:
# Detect URLs and convert to spoken form.
#   Remove the scheme entirely, meaning strip http:// and https:// and ftp://
#   Replace each dot with  dot
#   Replace each forward slash with  slash
#   Replace each hyphen with  hyphen
#   https://my-project.com/results  becomes  my hyphen project dot com slash results
#   www.google.com                  becomes  www dot google dot com

# RULE 6 - BRACKETS AND FORMATTING SYMBOLS:
# Remove ALL bracket characters.
# This includes round brackets, square brackets, curly brackets, and angle brackets.
# Remove ALL markdown and formatting symbols including asterisk, underscore, \
# tilde, pipe, backslash, hash, caret, backtick, and double quotes.
# Keep ONLY these punctuation marks which aid natural speech pacing: . , ? !
#   This is bold and important.
#   See link for details.

# RULE 7 - ABBREVIATIONS AND MATH SYMBOLS:
# Expand the following symbols to their full spoken equivalents.
#   & becomes and
#   % becomes percent
#   $ becomes dollars
#   + becomes plus
#   = becomes equals
#   e.g. becomes for example
#   i.e. becomes that is
#   vs. becomes versus
#   vs becomes versus
#   approx. becomes approximately
#   dept. becomes department
#   etc. becomes and so on

# RULE 8 - NUMBERS:
# Keep standard integers and decimals as-is since the TTS engine handles them.
# Do NOT rewrite numbers unless they are attached to symbols already handled above.
#   100 stays as 100
#   3.14 stays as 3.14
#   $500 becomes 500 dollars because the dollar symbol was expanded in Rule 7

# RULE 9 - WHITESPACE NORMALIZATION:
# This rule runs LAST as a final cleanup pass after all previous rules.
# Replace ALL consecutive whitespace characters including spaces, tabs, newlines, \
# and carriage returns with exactly ONE single space character.
# Strip all leading and trailing whitespace from the final output string.

# CRITICAL OUTPUT CONSTRAINTS:
# Output ONLY the final normalized speakable text string. Nothing else.
# Do NOT wrap the output in quotes of any kind.
# Do NOT add ANY conversational filler such as Sure, Here is the result, \
# Of course, Certainly, or I have normalized the text as follows.
# Do NOT include markdown formatting of any kind in the output.
# Do NOT explain, summarize, or describe what changes you made.
# Do NOT add a period at the end if the original text did not have one.
# If the input text is already fully clean and requires no changes, output it \
# exactly as-is without any modification.
# """

# # ---------------------------------------------------------------------------
# # Build chain — module level so it is initialized once at startup
# # ---------------------------------------------------------------------------
# _chain = None

# _llm_available = all([AZURE_API_KEY, AZURE_ENDPOINT, AZURE_DEPLOYMENT, AZURE_API_VERSION])

# if not _llm_available:
#     print(
#         "\n[llm_cleaner] WARNING: Azure OpenAI credentials incomplete.\n"
#         "  Check these keys in your .env:\n"
#         "    AZURE_OPENAI_API_KEY\n"
#         "    AZURE_OPENAI_ENDPOINT\n"
#         "    AZURE_OPENAI_MODEL_NAME\n"
#         "    AZURE_OPENAI_API_VERSION\n"
#         "  llm_clean_text() will return raw text as fallback.\n"
#     )
# else:
#     try:
#         _llm = AzureChatOpenAI(
#             azure_endpoint=AZURE_ENDPOINT,
#             api_key=AZURE_API_KEY,
#             azure_deployment=AZURE_DEPLOYMENT,
#             api_version=AZURE_API_VERSION,
#             # temperature=0 not supported by o4-mini — only default (1) is allowed
#             max_tokens=1024,
#         )

#         _prompt = ChatPromptTemplate.from_messages([
#             ("system", _SYSTEM_PROMPT),
#             ("human",  "{raw_text}"),
#         ])

#         _chain = _prompt | _llm | StrOutputParser()

#         print(f"[llm_cleaner] Chain ready  (deployment: {AZURE_DEPLOYMENT})")

#     except Exception as e:
#         print(f"[llm_cleaner] Init failed: {e}")
#         _chain = None


# # ---------------------------------------------------------------------------
# # Public API
# # ---------------------------------------------------------------------------

# def llm_clean_text(raw_text: str) -> str:
#     """
#     Normalize raw_text for TTS using Azure OpenAI.

#     Falls back to raw_text if Azure is unavailable or API call fails.
#     """
#     if not isinstance(raw_text, str):
#         raise TypeError(f"Expected str, got {type(raw_text).__name__}")

#     if not raw_text.strip():
#         return raw_text

#     if _chain is None:
#         print("[llm_cleaner] Chain not available — returning raw text.")
#         return raw_text

#     try:
#         print(f"[llm_cleaner] Normalizing {len(raw_text)} chars via Azure OpenAI...")

#         # Use llm directly instead of chain — o4-mini reasoning models
#         # sometimes return empty via StrOutputParser due to response format
#         from langchain_core.messages import HumanMessage, SystemMessage
#         messages = [
#             SystemMessage(content=_SYSTEM_PROMPT),
#             HumanMessage(content=raw_text),
#         ]
#         response = _llm.invoke(messages)

#         # Extract content safely — handles both str and list content types
#         raw_content = response.content
#         if isinstance(raw_content, list):
#             # Some models return list of content blocks
#             cleaned = " ".join(
#                 block.get("text", "") if isinstance(block, dict) else str(block)
#                 for block in raw_content
#             ).strip()
#         else:
#             cleaned = str(raw_content).strip()

#         print(f"[llm_cleaner] Raw response type : {type(raw_content).__name__}")
#         print(f"[llm_cleaner] Raw response value: {repr(raw_content[:200]) if isinstance(raw_content, str) else repr(raw_content)}")

#         if not cleaned:
#             print("[llm_cleaner] LLM returned empty string — using raw text.")
#             return raw_text

#         print(f"[llm_cleaner] Done. {len(raw_text)} -> {len(cleaned)} chars")

#         if cleaned != raw_text:
#             print(f"[llm_cleaner] Before : {raw_text[:120]}")
#             print(f"[llm_cleaner] After  : {cleaned[:120]}")

#         return cleaned

#     except Exception as e:
#         print(f"[llm_cleaner] Azure API error (fallback to raw text): {e}")
#         return raw_text























"""
llm_cleaner.py - Hybrid TTS Text Normalization

Strategy:
  Step 1 - Regex pre-pass  : Remove emojis, URLs, emails mechanically
                             (guaranteed, no LLM needed for these)
  Step 2 - LLM refinement  : Expand abbreviations, fix acronyms, 
                             normalize punctuation intelligently

This hybrid approach fixes o4-mini empty-response issues on
inputs that contain emojis + URLs + special chars together.
"""

import os
import re
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

load_dotenv()

AZURE_API_KEY     = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_ENDPOINT    = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_DEPLOYMENT  = os.getenv("AZURE_OPENAI_MODEL_NAME", "")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "")


def _regex_preprocess(text: str) -> str:
    """
    Mechanically remove/convert things that cause o4-mini to return empty:
      - Emojis and unicode symbols
      - URLs  
      - Emails
      - Dashes and hyphens
      - Leftover special characters
      - Extra whitespace
    """
    import emoji as emoji_lib

    # 1. Remove all emojis
    text = emoji_lib.replace_emoji(text, replace=" ")

    # 2. Convert emails BEFORE URLs (emails contain @ which URLs don't)
    # pattern: word@domain.tld
    text = re.sub(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
        lambda m: m.group(0).replace('@', ' at ').replace('.', ' dot '),
        text
    )

    # 3. Convert URLs to spoken form
    def url_to_spoken(m):
        url = m.group(0)
        url = re.sub(r'https?://', '', url) 
        url = re.sub(r'www\.', 'www dot ', url)
        url = url.replace('.', ' dot ')
        url = url.replace('/', ' slash ')
        url = url.replace('-', ' hyphen ')
        return url

    text = re.sub(r'https?://[^\s]+|www\.[^\s]+', url_to_spoken, text)

    # 4. Replace dashes and hyphens with space
    text = re.sub(r'[-–—]', ' ', text)

    # 5. Remove remaining special characters keep letters, digits, basic punctuation
    text = re.sub(r'[^a-zA-Z0-9\s.,?!\']', ' ', text)

    # 6. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


_REFINEMENT_PROMPT = """\
You are a TTS Text Normalization Node. The input text has already been \
pre-processed to remove emojis and convert URLs and emails. 
Your job is to apply these final refinements only:

RULE 1 - ACRONYMS AND INITIALISMS:
Separate each letter of ALL-CAPS sequences with a single space.
  API becomes A P I
  GFPGAN becomes G F P G A N
  UCP becomes U C P
  FYP becomes F Y P
  AI becomes A I
Do NOT split mixed-case words like Google or Pakistan.

RULE 2 - ABBREVIATIONS AND SYMBOLS:
Expand to spoken equivalents:
  & becomes and
  % becomes percent
  $ becomes dollars
  + becomes plus
  = becomes equals
  e.g. becomes for example
  i.e. becomes that is
  vs becomes versus
  approx becomes approximately
  etc becomes and so on

RULE 3 - WHITESPACE:
Normalize all consecutive spaces into one single space.
Strip leading and trailing whitespace.

CRITICAL OUTPUT RULES:
Output ONLY the final normalized text. Nothing else.
No quotes. No explanations. No filler words like Sure or Here is the result.
If nothing needs to change, return the text exactly as given.
"""


_llm = None
_llm_available = all([AZURE_API_KEY, AZURE_ENDPOINT, AZURE_DEPLOYMENT, AZURE_API_VERSION])

if not _llm_available:
    print(
        "\n[llm_cleaner] WARNING: Azure OpenAI credentials incomplete.\n"
        "  Will use regex-only mode (no LLM refinement).\n"
    )
else:
    try:
        _llm = AzureChatOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=AZURE_API_KEY,
            azure_deployment=AZURE_DEPLOYMENT,
            api_version=AZURE_API_VERSION,
            max_tokens=1024,
        )
        print(f"[llm_cleaner] Chain ready  (deployment: {AZURE_DEPLOYMENT})")
    except Exception as e:
        print(f"[llm_cleaner] Init failed: {e}")
        _llm = None


def llm_clean_text(raw_text: str) -> str:
    """
    Hybrid TTS normalizer: regex pre-pass + LLM refinement.

    Step 1 (always): Regex removes emojis, converts URLs/emails, strips symbols.
    Step 2 (if LLM available): LLM expands acronyms and abbreviations.

    Falls back gracefully at every step — never crashes.
    """
    if not isinstance(raw_text, str):
        raise TypeError(f"Expected str, got {type(raw_text).__name__}")

    if not raw_text.strip():
        return raw_text

    print(f"[llm_cleaner] Input  : {raw_text[:120]}")


    try:
        after_regex = _regex_preprocess(raw_text)
        print(f"[llm_cleaner] Regex  : {after_regex[:120]}")
    except Exception as e:
        print(f"[llm_cleaner] Regex error: {e} using raw text")
        after_regex = raw_text


    if _llm is None:
        print("[llm_cleaner] LLM not available regex result used.")
        return after_regex

    try:
        messages = [
            SystemMessage(content=_REFINEMENT_PROMPT),
            HumanMessage(content=after_regex),
        ]
        response = _llm.invoke(messages)

        raw_content = response.content
        if isinstance(raw_content, list):
            cleaned = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_content
            ).strip()
        else:
            cleaned = str(raw_content).strip()

        if not cleaned:
            print("[llm_cleaner] LLM returned empty using regex result.")
            return after_regex

        print(f"[llm_cleaner] Final  : {cleaned[:120]}")
        print(f"[llm_cleaner] Chars  : {len(raw_text)} -> {len(cleaned)}")
        return cleaned

    except Exception as e:
        print(f"[llm_cleaner] LLM error (using regex result): {e}")
        return after_regex
