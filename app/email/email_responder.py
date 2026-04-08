import re
import logging
from typing import Dict, Any, Optional, Tuple

from app.rag.rag_pipeline import RAGPipeline
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt
from ibtcode import IbtcodeSystem
from ibtcode.models import IbtcodeState, Decision, Emotion, Intent, Context, Strategy


class EmailResponder:

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.rag = RAGPipeline(user_id)
        self.llm = LLMClient()
        self.decision_engine = IbtcodeSystem(memory_size=10)
        
        logging.info(f"EmailResponder initialized for user: {user_id}")

    def clean_response(self, response: str) -> str:
        """Clean LLM output"""
        if "Subject:" in response:
            response = response[response.index("Subject:"):]
        return response.strip()

    def extract_order_id(self, text: str) -> Optional[str]:
        """Extract order ID from text"""
        match = re.search(r"\b\d{5,}\b", text)
        return match.group() if match else None

    def extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text"""
        match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )
        return match.group() if match else None

    def extract_ticket_id(self, text: str) -> Optional[str]:
        """Extract ticket ID from text"""
        match = re.search(r"\bT\d+\b", text, re.IGNORECASE)
        return match.group() if match else None

    def extract_project_name(self, text: str) -> Optional[str]:
        """Extract project name from text"""
        match = re.search(r'project\s+"([^"]+)"', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r'([A-Za-z\s]+)\s+project', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None

    def search_documents(self, keyword: str) -> list:
        """Search documents by keyword"""
        results = []
        keyword = keyword.lower()
        
        for doc in self.rag.documents:
            if keyword in doc["text"].lower():
                results.append(doc["text"])
                if len(results) >= 3:
                    break
        
        return results

    def analyze_with_decision_layer(self, customer_email: str) -> Tuple[IbtcodeState, Decision]:
        """
        Analyze customer email using Ibtcode decision layer.
        Returns state and decision for informed response generation.
        """
        _, state, decision = self.decision_engine.process(customer_email)
        
        logging.info(f"Decision Layer Analysis:")
        logging.info(f"  Emotion: {state.emotion} (level {state.emotion_level})")
        logging.info(f"  Intent: {state.intent}")
        logging.info(f"  Context: {state.context}")
        logging.info(f"  Risk: {state.risk}")
        logging.info(f"  Urgency: {state.urgency}")
        logging.info(f"  Strategy: {decision.strategy}")
        logging.info(f"  Priority: {state.priority}")
        
        return state, decision

    def get_response_strategy_guidance(self, state: IbtcodeState, decision: Decision) -> str:
        """
        Generate guidance for LLM based on decision layer output.
        """
        guidance_map = {
            Strategy.DE_ESCALATE: """
CRITICAL GUIDANCE:
- Customer is highly frustrated or angry
- Response must be empathetic and apologetic
- Prioritize quick resolution
- Use calming language
- Acknowledge the problem immediately
""",
            Strategy.CLARIFY: """
CRITICAL GUIDANCE:
- Customer message is unclear or confused
- Ask specific clarifying questions
- Do not assume what customer needs
- Request missing information politely
""",
            Strategy.EXPLAIN: """
CRITICAL GUIDANCE:
- Customer needs explanation or guidance
- Provide step-by-step instructions
- Be detailed but clear
- Avoid technical jargon
""",
            Strategy.SUPPORT: """
CRITICAL GUIDANCE:
- Customer needs support with an issue
- Show understanding of frustration
- Offer concrete solutions
- Be helpful and patient
""",
            Strategy.EMPATHIZE: """
CRITICAL GUIDANCE:
- Customer is sad or anxious
- Show genuine empathy
- Reassure the customer
- Be gentle and supportive
""",
            Strategy.APOLOGIZE: """
CRITICAL GUIDANCE:
- There is an error or failure
- Apologize sincerely
- Take responsibility
- Explain next steps for resolution
""",
            Strategy.NORMAL: """
CRITICAL GUIDANCE:
- Standard customer inquiry
- Respond professionally and helpfully
- Be concise and clear
"""
        }
        
        base_guidance = guidance_map.get(decision.strategy, guidance_map[Strategy.NORMAL])
        
        # Add emotion-specific guidance
        emotion_guidance = {
            Emotion.ANGRY: "Customer is angry. Stay calm and professional. Do not argue.",
            Emotion.FRUSTRATED: "Customer is frustrated. Acknowledge their effort so far.",
            Emotion.CONFUSED: "Customer is confused. Be very clear and simple.",
            Emotion.ANXIOUS: "Customer is anxious. Provide reassurance and certainty.",
            Emotion.SAD: "Customer is sad. Be empathetic and understanding.",
        }
        
        emotion_specific = emotion_guidance.get(state.emotion, "")
        
        # Add risk and urgency flags
        risk_guidance = ""
        if state.risk >= 4:
            risk_guidance = "\nHIGH RISK: This requires immediate attention and escalation if needed."
        elif state.urgency >= 4:
            risk_guidance = "\nHIGH URGENCY: Respond quickly and prioritize this customer."
        
        return f"{base_guidance}\n{emotion_specific}\n{risk_guidance}"

    def generate_reply(self, customer_email: str) -> Dict[str, Any]:
        """
        Main pipeline: Analyze with decision layer, then generate response.
        """
        logging.info("Processing new customer email")
        
        # Step 1: Analyze with decision layer
        state, decision = self.analyze_with_decision_layer(customer_email)
        
        # Step 2: Extract identifiers
        order_id = self.extract_order_id(customer_email)
        email_id = self.extract_email(customer_email)
        ticket_id = self.extract_ticket_id(customer_email)
        project_name = self.extract_project_name(customer_email)
        
        # Step 3: Retrieve context based on extracted IDs
        retrieved_context = []
        
        if project_name:
            logging.info(f"Searching project: {project_name}")
            retrieved_context = self.search_documents(project_name)
        
        if not retrieved_context and order_id:
            logging.info(f"Searching order: {order_id}")
            retrieved_context = self.search_documents(order_id)
        
        if not retrieved_context and ticket_id:
            logging.info(f"Searching ticket: {ticket_id}")
            retrieved_context = self.search_documents(ticket_id)
        
        if not retrieved_context and email_id:
            logging.info(f"Searching email: {email_id}")
            retrieved_context = self.search_documents(email_id)
        
        if not retrieved_context:
            logging.info("Using vector search fallback")
            retrieved_context = self.rag.retrieve(customer_email)
        
        # Step 4: Get strategy guidance from decision layer
        strategy_guidance = self.get_response_strategy_guidance(state, decision)
        
        # Step 5: Build prompt with decision layer insights
        prompt = build_email_prompt(
            customer_email=customer_email,
            retrieved_context=retrieved_context,
            decision_state=state,
            decision_output=decision,
            strategy_guidance=strategy_guidance
        )
        
        # Step 6: Generate LLM response
        response = self.llm.generate(prompt)
        response = self.clean_response(response)
        
        # Step 7: Return complete analysis with response
        return {
            "response": response,
            "analysis": {
                "emotion": state.emotion,
                "emotion_level": state.emotion_level,
                "intent": state.intent,
                "context": state.context,
                "risk": state.risk,
                "urgency": state.urgency,
                "priority": state.priority,
                "strategy": decision.strategy.value,
                "action": decision.action.value,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning
            },
            "identifiers": {
                "order_id": order_id,
                "ticket_id": ticket_id,
                "project_name": project_name,
                "email": email_id
            }
        }