import logging
from typing import List
from app.models.prompt_engine import SemanticFacts, Entity, Statement

logger = logging.getLogger(__name__)

class SemanticValidator:
    def validate_and_sanitize(self, facts: SemanticFacts) -> SemanticFacts:
        """Strict local verification of semantic facts before compilation."""
        valid_entity_ids = {e.id for e in facts.entities if e.id and e.name.strip()}
        
        # Filter entities
        clean_entities = [e for e in facts.entities if e.id and e.name.strip()]
        
        # Filter and sanitize statements
        clean_statements = []
        for s in facts.statements:
            if not s.text.strip():
                continue
            
            # Check subject existence
            if s.subject and s.subject not in valid_entity_ids:
                logger.warning(f"Statement subject '{s.subject}' not found in entities. Setting subject to None.")
                s.subject = None
                
            # Check target existence
            if s.target and s.target not in valid_entity_ids:
                logger.warning(f"Statement target '{s.target}' not found in entities. Setting target to None.")
                s.target = None

            # Clean text
            s.text = s.text.strip()
            clean_statements.append(s)

        return SemanticFacts(entities=clean_entities, statements=clean_statements)
