"""
Part 3 — GenAI-Powered Insight Narrator (SCR: Situation, Complication, Resolution)

Reads narrator/findings.json (written by analysis/clean_and_eda.py) and writes a
business narrative for Mamaearth's regional ops and finance heads.

  - Online path : Gemini (free Google AI Studio key), used if GEMINI_API_KEY is set
  - Offline path: a fixed template, used if there is no key or the API call fails

Usage (from the project root):
    python narrator/generate_narrative.py                  # Gemini if key set, else offline
    python narrator/generate_narrative.py --check-sample   # check the saved Gemini sample
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import json
import osf
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# Task 4 — Offline fallback (no internet, no API key)
# ---------------------------------------------------------------------------
def generate_scr_narrative_offline(findings):
    """Builds the SCR narrative from a template. No internet, no API key."""
    f = findings
    rr = f["return_rate_by_payment"]
    seg = f["highest_risk_segment"]
    peak = f["true_peak_month"]
    infl = f["outlier_inflated_month"]

    peak_name = datetime.strptime(peak["month"], "%Y-%m").strftime("%B")   # "March"
    infl_name = datetime.strptime(infl["month"], "%Y-%m").strftime("%B")   # "January"

    narrative = f"""Situation:
Mamaearth's cleaned revenue for Jan-Jun 2026 is Rs {f['cleaned_total_revenue_inr']:,.2f}.
The raw total of Rs {f['raw_total_revenue_inr']:,.2f} was overstated by Rs {f['duplicate_reconciliation_delta_inr']:,.2f}
because of duplicate orders. {peak_name} is the true peak month at Rs {peak['revenue_inr']:,.2f};
{infl_name} only looked bigger (Rs {infl['apparent_revenue_inr']:,.2f}) because of two bulk orders.

Complication:
COD orders are returned at {rr['COD']}%, compared with {rr['UPI']}% for UPI and {rr['CARD']}% for Card.
The worst segment is {seg['payment_method']} in Tier-{seg['city_tier']} cities at {seg['return_rate_pct']}%.

Resolution:
1) Push prepaid payment (UPI/Card) in Tier-{seg['city_tier']} cities first.
2) Report revenue on the de-duplicated basis and fix the double-submit bug.
3) Plan seasonality around {peak_name}, not {infl_name}.
"""
    return {"status": "success", "narrative": narrative, "tokens": None}


# ---------------------------------------------------------------------------
# Task 5 — Numeric accuracy checker
# ---------------------------------------------------------------------------
def check_narrative(text, findings):
    """Checks the 5 required figures are in the text. Prints PASS/FAIL for each."""
    t = text.replace(",", "")      # "97,358.30" becomes "97358.30"
    peak_name = datetime.strptime(findings["true_peak_month"]["month"], "%Y-%m").strftime("%B")

    checks = [
        ("Cleaned revenue",    str(findings["cleaned_total_revenue_inr"])),
        ("COD return rate",    str(findings["return_rate_by_payment"]["COD"])),
        ("COD Tier-2 rate",    str(findings["highest_risk_segment"]["return_rate_pct"])),
        ("Duplicate delta",    str(findings["duplicate_reconciliation_delta_inr"])),
        ("Peak month revenue", str(findings["true_peak_month"]["revenue_inr"])),
    ]

    all_ok = True
    for label, value in checks:
        ok = value in t
        if label == "Peak month revenue":
            ok = ok and peak_name in text      # "March" must also appear
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: {value}")
        all_ok = all_ok and ok

    print("=> ALL 5 PASSED" if all_ok else "=> CHECK FAILED")
    return all_ok


# ---------------------------------------------------------------------------
# Tasks 2 + 3 — Gemini narrative with locked parameters and error handling
# ---------------------------------------------------------------------------
MODEL = "models/gemini-3.5-flash"     # free-tier flash model

SYSTEM_INSTRUCTION = (
    "You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
    "Write a concise business narrative (about 250 words) with exactly three labelled sections: "
    "'Situation:', 'Complication:' and 'Resolution:'. "
    "Every number you write must come from the findings provided and appear with exactly the same value. "
    "Do not invent, estimate or calculate any new statistics. "
    "Write rupee amounts like Rs 12,345.60 and percentages with one decimal. "
    "Refer to months by their full English name. Plain text only, no markdown."
)


def build_prompt(findings):
    """Builds the user prompt from the findings dict. No numbers are typed here."""
    f = findings
    rr = f["return_rate_by_payment"]
    seg = f["highest_risk_segment"]
    peak = f["true_peak_month"]
    infl = f["outlier_inflated_month"]
    peak_name = datetime.strptime(peak["month"], "%Y-%m").strftime("%B %Y")
    infl_name = datetime.strptime(infl["month"], "%Y-%m").strftime("%B %Y")

    return f"""Write the SCR narrative using ONLY these verified findings (Jan-Jun 2026):
- Cleaned total revenue: Rs {f['cleaned_total_revenue_inr']:,.2f}
- Raw total revenue before cleaning: Rs {f['raw_total_revenue_inr']:,.2f}
- Revenue overstated by duplicate orders: Rs {f['duplicate_reconciliation_delta_inr']:,.2f}
- Return rate by payment method: COD {rr['COD']}%, CARD {rr['CARD']}%, UPI {rr['UPI']}%
- Highest-risk segment: {seg['payment_method']} in Tier-{seg['city_tier']} cities at {seg['return_rate_pct']}%
- True peak month (after removing two bulk outlier orders): {peak_name} at Rs {peak['revenue_inr']:,.2f}
- {infl_name} only looked like the peak at Rs {infl['apparent_revenue_inr']:,.2f}; corrected it is Rs {infl['corrected_revenue_inr']:,.2f}
"""


def generate_scr_narrative(findings):
    """Gemini SCR narrative. Falls back to the offline template if there's no key or the call fails."""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        result = {"status": "error", "narrative": None, "message": "No GEMINI_API_KEY set"}
    else:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,          # role + structure + number rule, kept separate
                temperature=0.0,                                # deterministic: a factual business report, not creative writing
                max_output_tokens=8192,                         # explicit cap (>= 300); newer models also spend tokens on reasoning
                http_options=types.HttpOptions(timeout=30000),  # 30-second timeout (milliseconds)
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # no tools used
            )
            response = client.models.generate_content(
                model=MODEL,
                contents=build_prompt(findings),
                config=config,
            )
            finish = str(response.candidates[0].finish_reason)
            if "MAX_TOKENS" in finish or not response.text:
                raise RuntimeError(f"Gemini output incomplete (finish_reason={finish})")
            result = {
                "status": "success",
                "narrative": response.text,
                "tokens": response.usage_metadata.total_token_count,
            }
        except Exception as err:
            result = {"status": "error", "narrative": None, "message": str(err)}

    # Task 4: fall back to the offline template on any error
    if result["status"] == "error":
        print("Online path unavailable:", result["message"], "-> using offline template")
        return generate_scr_narrative_offline(findings)
    return result


# ---------------------------------------------------------------------------
# Main — runs only when this file is executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Load the verified figures written by analysis/clean_and_eda.py
    with open("narrator/findings.json", encoding="utf-8") as f:
        findings = json.load(f)

    # Option: check the saved Gemini sample instead of generating a new one
    if "--check-sample" in sys.argv:
        with open("narrator/sample_output.txt", encoding="utf-8") as f:
            print("Checking saved Gemini sample: narrator/sample_output.txt")
            ok = check_narrative(f.read(), findings)
        sys.exit(0 if ok else 1)

    # Normal run: Gemini if GEMINI_API_KEY is set, otherwise the offline template
    result = generate_scr_narrative(findings)
    print(f"status: {result['status']} | tokens: {result.get('tokens')}")
    print("-" * 60)
    print(result["narrative"])
    print("-" * 60)
    check_narrative(result["narrative"], findings)