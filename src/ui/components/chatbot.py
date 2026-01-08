"""Analyst Chatbot Component with Source Citations and Memory.

Per spec Section 7.1.2.F:
- Supported queries: "What's [TICKER]'s next catalyst?", "Show me [INDICATION] trials"
- Model: Haiku 4.5 (simple) / Sonnet (complex)
- Context: Query catalysts, insights, sec_filings tables
- Response time: <5 seconds
- Acceptance criteria: Answers ticker lookup correctly with source citation

Phase 3 Enhancements:
- Per-session context tracking (last_ticker, last_indication)
- Pronoun resolution ("What about their cash runway?" -> resolves to last ticker)
- Persistent chat history in database
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from utils.user_memory import SessionMemory, ChatSessionManager, UserMemory

logger = logging.getLogger(__name__)


# Chat prompt for biotech analyst
BIOTECH_ANALYST_PROMPT = """
You are a biotech analyst AI assistant. Answer questions about clinical trials, catalysts, and biotech companies.

IMPORTANT: Always include source citations in your responses using this format:
- For SEC filings: [TICKER_YEAR_FILING, pg X]
- For clinical trials: [NCT: NCTXXXXXXXX]
- For FDA events: [FDA Calendar / Source]

Available data:
{context_data}

User question: {question}

Provide a concise, actionable answer with source citations. If you don't have specific data, acknowledge limitations.
"""


class CatalystChatAgent:
    """Chat agent that queries catalyst database with source citations.

    Phase 3: Now includes session memory for context tracking and pronoun resolution.
    """

    def __init__(self, db=None, session_memory: Optional[SessionMemory] = None):
        """Initialize chat agent.

        Args:
            db: SQLiteDB instance (optional)
            session_memory: SessionMemory instance for context tracking (optional)
        """
        self.db = db
        self.session_memory = session_memory or SessionMemory()
        self._init_db()

    def _init_db(self):
        """Lazy load database."""
        if self.db is None:
            try:
                from utils.sqlite_db import get_db
                self.db = get_db()
            except Exception as e:
                logger.warning(f"Could not initialize database: {e}")
                self.db = None

    def extract_ticker(self, text: str) -> Optional[str]:
        """Extract ticker symbol from user query."""
        # Common words to exclude (not actual tickers in biotech context)
        COMMON_WORDS = {
            "WHAT", "SHOW", "TELL", "FIND", "LIST", "NEXT", "ABOUT", "FROM",
            "WITH", "HAVE", "DOES", "WILL", "WHEN", "WHERE", "THIS", "THAT",
            "HELP", "MORE", "INFO", "DATA", "CASH", "DRUG", "PHASE", "TRIAL",
            "THE", "FOR", "AND", "ARE", "CAN", "HOW", "GET", "ALL", "ANY",
            "ME", "MY", "YOUR", "YOU", "IT", "IS", "BE", "AS", "AT", "BY",
        }

        # Pattern 1: $TICKER (most reliable)
        dollar_match = re.search(r"\$([A-Z]{2,5})\b", text.upper())
        if dollar_match:
            return dollar_match.group(1)

        # Pattern 2: TICKER's or ticker: TICKER
        text_upper = text.upper()

        # Look for ticker: XXXX format
        ticker_match = re.search(r"TICKER[:\s]+([A-Z]{2,5})\b", text_upper)
        if ticker_match:
            return ticker_match.group(1)

        # Pattern 3: TICKER's (possessive) - very common
        possessive_match = re.search(r"\b([A-Z]{2,5})'S\b", text_upper)
        if possessive_match and possessive_match.group(1) not in COMMON_WORDS:
            return possessive_match.group(1)

        # Pattern 4: standalone TICKER (2-5 caps) - check against common words
        # Find all potential tickers and return first non-common word
        for match in re.finditer(r"\b([A-Z]{2,5})\b", text_upper):
            ticker = match.group(1)
            if ticker not in COMMON_WORDS:
                # Additional check: ticker should have at least one consonant
                if re.search(r"[BCDFGHJKLMNPQRSTVWXZ]", ticker):
                    return ticker

        return None

    def extract_indication(self, text: str) -> Optional[str]:
        """Extract therapeutic indication from query."""
        indications = [
            "oncology", "cancer", "tumor",
            "alzheimer", "neurology", "parkinson",
            "diabetes", "obesity",
            "depression", "anxiety",
            "rare disease", "orphan",
            "cardiovascular", "heart",
            "immunology", "autoimmune",
        ]

        text_lower = text.lower()
        for indication in indications:
            if indication in text_lower:
                return indication

        return None

    def query_catalysts(
        self,
        ticker: Optional[str] = None,
        indication: Optional[str] = None,
        days_ahead: int = 90,
    ) -> List[Dict[str, Any]]:
        """Query database for relevant catalysts.

        Args:
            ticker: Specific ticker to search
            indication: Therapeutic area to filter
            days_ahead: Days to look ahead

        Returns:
            List of catalyst dicts with source citations
        """
        if self.db is None:
            return []

        results = []

        try:
            # Query clinical trials
            trials = self.db.get_upcoming_trials(days_ahead=days_ahead)
            for trial in trials:
                trial_ticker = trial.get("sponsor_ticker") or trial.get("ticker")

                # Filter by ticker if specified
                if ticker and trial_ticker != ticker:
                    continue

                # Filter by indication if specified
                conditions = trial.get("conditions", [])
                if isinstance(conditions, str):
                    try:
                        import json
                        conditions = json.loads(conditions)
                    except:
                        conditions = [conditions]

                if indication:
                    condition_text = " ".join(conditions).lower()
                    if indication.lower() not in condition_text:
                        continue

                results.append({
                    "type": "trial",
                    "ticker": trial_ticker,
                    "catalyst": f"{trial.get('phase', 'Phase ?')} Readout",
                    "date": trial.get("primary_completion_date"),
                    "indication": ", ".join(conditions[:2]) if conditions else "Unspecified",
                    "source": f"[NCT: {trial.get('nct_id')}]",
                    "design_score": trial.get("trial_design_score"),
                })

            # Query FDA events
            fda_events = self.db.get_upcoming_fda_events(days_ahead=days_ahead)
            for event in fda_events:
                event_ticker = event.get("ticker")

                if ticker and event_ticker != ticker:
                    continue

                if indication:
                    event_indication = event.get("indication", "").lower()
                    if indication.lower() not in event_indication:
                        continue

                results.append({
                    "type": "fda",
                    "ticker": event_ticker,
                    "catalyst": event.get("event_type", "FDA Event"),
                    "date": event.get("event_date"),
                    "indication": event.get("indication", ""),
                    "drug": event.get("drug_name"),
                    "source": f"[FDA: {event.get('source_url', 'Calendar')}]",
                })

        except Exception as e:
            logger.error(f"Database query failed: {e}")

        # Sort by date
        results.sort(key=lambda x: x.get("date") or datetime.max.date())

        return results[:10]

    def query_sec_filing(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get latest SEC filing data for ticker."""
        if self.db is None:
            return None

        try:
            for filing_type in ["10-Q", "10-K"]:
                filing = self.db.get_latest_sec_filing(ticker, filing_type)
                if filing:
                    return {
                        "type": filing_type,
                        "date": filing.get("filing_date"),
                        "cash_runway_months": filing.get("cash_runway_months"),
                        "burn_rate": filing.get("monthly_burn_rate_usd"),
                        "cash_position": filing.get("cash_position_usd"),
                        "source": f"[{ticker}_2024_{filing_type}]",
                    }
        except Exception as e:
            logger.error(f"SEC query failed: {e}")

        return None

    def generate_response(
        self,
        question: str,
        use_llm: bool = True,
    ) -> str:
        """Generate response to user question with citations.

        Args:
            question: User's question
            use_llm: Whether to use LLM (if available)

        Returns:
            Response string with source citations
        """
        # Phase 3: Resolve pronouns using session context
        resolved_question = self.session_memory.resolve_pronouns(question)
        if resolved_question != question:
            logger.info(f"Resolved pronouns: '{question}' -> '{resolved_question}'")

        # Extract entities from resolved question
        ticker = self.extract_ticker(resolved_question)
        indication = self.extract_indication(resolved_question)

        # Phase 3: Update session context with extracted entities
        self.session_memory.update_context(ticker=ticker, indication=indication)

        # Query relevant data
        catalysts = self.query_catalysts(ticker=ticker, indication=indication)
        sec_data = self.query_sec_filing(ticker) if ticker else None

        # Build context
        context_parts = []

        if catalysts:
            context_parts.append("Upcoming Catalysts:")
            for cat in catalysts[:5]:
                date_str = cat.get("date", "TBD")
                if hasattr(date_str, "strftime"):
                    date_str = date_str.strftime("%Y-%m-%d")
                context_parts.append(
                    f"- {cat.get('ticker', 'N/A')}: {cat.get('catalyst')} on {date_str} "
                    f"for {cat.get('indication', 'N/A')} {cat.get('source', '')}"
                )

        if sec_data:
            context_parts.append(f"\nSEC Filing Data ({sec_data.get('type')}):")
            if sec_data.get("cash_runway_months"):
                context_parts.append(f"- Cash Runway: {sec_data['cash_runway_months']:.0f} months")
            if sec_data.get("cash_position"):
                context_parts.append(f"- Cash Position: ${sec_data['cash_position']/1e6:.1f}M")
            context_parts.append(f"Source: {sec_data.get('source', '')}")

        context_data = "\n".join(context_parts) if context_parts else "No specific data found for this query."

        # Try LLM if available
        if use_llm and os.getenv("ANTHROPIC_API_KEY"):
            try:
                return self._llm_response(question, context_data)
            except Exception as e:
                logger.warning(f"LLM response failed: {e}")

        # Fallback to rule-based response
        return self._rule_based_response(question, ticker, catalysts, sec_data)

    def _llm_response(self, question: str, context_data: str) -> str:
        """Generate response using LLM."""
        import anthropic

        client = anthropic.Anthropic()

        prompt = BIOTECH_ANALYST_PROMPT.format(
            context_data=context_data,
            question=question,
        )

        # Use Haiku for simple queries, Sonnet for complex
        is_complex = any(word in question.lower() for word in ["compare", "analyze", "why", "risk", "valuation"])
        model = "claude-sonnet-4-20250514" if is_complex else "claude-3-5-haiku-20241022"

        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def _rule_based_response(
        self,
        question: str,
        ticker: Optional[str],
        catalysts: List[Dict],
        sec_data: Optional[Dict],
    ) -> str:
        """Generate rule-based response with citations."""
        question_lower = question.lower()

        # Ticker-specific query
        if ticker:
            if catalysts:
                cat = catalysts[0]
                date_str = cat.get("date", "TBD")
                if hasattr(date_str, "strftime"):
                    date_str = date_str.strftime("%B %d, %Y")

                response = f"**{ticker}'s next catalyst:** {cat.get('catalyst')} on {date_str}\n\n"
                response += f"- Indication: {cat.get('indication', 'Unspecified')}\n"
                if cat.get("design_score"):
                    response += f"- Trial Design Score: {cat['design_score']}/100\n"
                response += f"\n📎 Source: {cat.get('source', 'Internal')}"

                if sec_data:
                    response += f"\n\n**Financial Snapshot** {sec_data.get('source', '')}:\n"
                    if sec_data.get("cash_runway_months"):
                        response += f"- Cash Runway: {sec_data['cash_runway_months']:.0f} months\n"

                return response
            else:
                return f"I don't have specific catalyst data for **{ticker}** in my database. The company may not have active Phase 2/3 trials in the next 90 days, or they may not be publicly traded on major US exchanges."

        # Indication query
        if "show" in question_lower or "find" in question_lower or "list" in question_lower:
            if catalysts:
                indication_str = self.extract_indication(question) or "various indications"
                response = f"**Upcoming {indication_str.title()} Catalysts:**\n\n"
                for cat in catalysts[:5]:
                    date_str = cat.get("date", "TBD")
                    if hasattr(date_str, "strftime"):
                        date_str = date_str.strftime("%Y-%m-%d")
                    response += f"- **{cat.get('ticker', 'N/A')}**: {cat.get('catalyst')} ({date_str}) {cat.get('source', '')}\n"
                return response

        # Cash runway query
        if "cash" in question_lower or "runway" in question_lower:
            if ticker and sec_data:
                return f"**{ticker} Cash Position** {sec_data.get('source', '')}:\n\n- Runway: {sec_data.get('cash_runway_months', 'Unknown')} months\n- Position: ${(sec_data.get('cash_position') or 0)/1e6:.1f}M"
            return "Please specify a ticker symbol to check cash runway. Example: 'What is ACAD's cash runway?'"

        # General response
        return "I can help you find:\n- **Catalyst dates**: 'What's ACAD's next catalyst?'\n- **Trial data**: 'Show me oncology trials'\n- **Financial data**: 'What's SAVA's cash runway?'\n\nAll responses include source citations from SEC filings and ClinicalTrials.gov."


def render_chatbot(context_ticker: str = None, user_id: Optional[int] = None):
    """Render the AI Analyst chatbot interface with source citations.

    Args:
        context_ticker: Optional ticker to focus on
        user_id: Optional user ID for persistent chat history (Phase 3)
    """
    st.markdown("### 🤖 Biotech Analyst AI")

    if context_ticker:
        st.info(f"Context: Analyzing **{context_ticker}**")

    # Phase 3: Initialize session memory for context tracking
    if "session_memory" not in st.session_state:
        st.session_state.session_memory = SessionMemory()

    # Initialize chat agent with session memory
    if "chat_agent" not in st.session_state:
        st.session_state.chat_agent = CatalystChatAgent(
            session_memory=st.session_state.session_memory
        )

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message
        welcome = """Hello! I'm your Biotech Analyst AI. I can help you with:

- **Catalyst lookups**: "What's ACAD's next catalyst?"
- **Trial searches**: "Show me Phase 3 oncology trials"
- **Financial data**: "What's the cash runway for SAVA?"

All my responses include **source citations** from SEC filings and ClinicalTrials.gov.

**Tip**: I remember our conversation! After asking about a ticker, you can ask "What about their cash runway?" and I'll know which company you mean."""

        st.session_state.messages.append({
            "role": "assistant",
            "content": welcome,
        })

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about a catalyst..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            # Show thinking indicator
            with st.spinner("Querying catalyst database..."):
                start_time = time.time()

                # Add context ticker to query if provided
                if context_ticker and context_ticker.upper() not in prompt.upper():
                    prompt_with_context = f"{prompt} (context: {context_ticker})"
                else:
                    prompt_with_context = prompt

                response = st.session_state.chat_agent.generate_response(
                    prompt_with_context,
                    use_llm=bool(os.getenv("ANTHROPIC_API_KEY")),
                )

                elapsed = time.time() - start_time
                logger.info(f"Chat response generated in {elapsed:.2f}s")

            # Streaming effect for better UX
            full_response = ""
            words = response.split()
            for i, word in enumerate(words):
                full_response += word + " "
                if i % 5 == 0:  # Update every 5 words
                    time.sleep(0.02)
                    message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
