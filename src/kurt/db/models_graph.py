from enum import Enum


class EntityType(Enum):
    # THE CORE
    PRODUCT = "Product"
    ORG = "Organization"

    # THE CAPABILITIES
    FEATURE = "Feature"
    INTEGRATION = "Integration"

    # THE IMPLEMENTATION
    SYNTAX = "Syntax"
    PRIMITIVE = "Primitive"

    # THE RULES
    POLICY = "Policy"

    @classmethod
    def get_metadata(cls, entity_type: "EntityType") -> dict:
        """Centralized metadata to drive the prompt generation."""
        metadata = {
            cls.PRODUCT: {
                "desc": "Named software platforms or services.",
                "examples": ["MotherDuck", "DuckDB", "BigQuery"],
                "trigger": "Proper nouns of software products.",
            },
            cls.ORG: {
                "desc": "Companies or groups behind technologies.",
                "examples": ["OpenAI", "Google", "DuckDB Labs"],
                "trigger": "Brand names or organizational entities.",
            },
            cls.FEATURE: {
                "desc": "High-level capabilities or conceptual methods.",
                "examples": ["Semantic Search", "Hybrid Search", "RAG"],
                "trigger": "Conceptual functionality (the 'What').",
            },
            cls.INTEGRATION: {
                "desc": "Connection points or external dependencies.",
                "examples": ["OpenAI API", "S3 Storage", "Python SDK"],
                "trigger": "References to 'connecting to', 'calling', or 'using via'.",
            },
            cls.SYNTAX: {
                "desc": "Literal code, functions, or SQL operators.",
                "examples": [
                    "embedding()",
                    "UPDATE",
                    "CREATE TABLE AS",
                    "array_cosine_similarity()",
                ],
                "trigger": "Actual code snippets or function names (the 'How').",
            },
            cls.PRIMITIVE: {
                "desc": "Fundamental data objects or formats.",
                "examples": ["Vectors", "Embeddings", "Parquet files", "Tokens"],
                "trigger": "Data structures or objects being manipulated.",
            },
            cls.POLICY: {
                "desc": "Limits, quotas, and behavioral constraints.",
                "examples": ["1M rows/day", "Free Tier limits", "Standard Plan"],
                "trigger": "Mentions of 'limited to', 'quota', 'cost per', or 'requirements'.",
            },
        }
        return metadata.get(entity_type, {})

    @classmethod
    def get_extraction_rules(cls) -> str:
        """Generates a high-fidelity prompt block for DSPy/LLM instruction."""
        rules = [
            "### 1. ENTITY TAXONOMY & DEFINITIONS",
            "Extract entities based on these strict category definitions:",
        ]

        for et in cls:
            meta = cls.get_metadata(et)
            rules.append(f"- **{et.value}**: {meta['desc']}")
            rules.append(f"  * Examples: {', '.join(meta['examples'])}")
            rules.append(f"  * Detection Trigger: {meta['trigger']}")

        rules.extend(
            [
                "",
                "### 2. CORE EXTRACTION LOGIC",
                "1. CONCEPT VS CODE: Do not confuse Feature and Syntax. 'Semantic Search' is a Feature; 'embedding()' is Syntax.",
                "2. LITERAL SYNTAX: Always extract the exact function name for Syntax (e.g., extract 'UPDATE', not 'the update command').",
                "3. DATA OBJECTS: If a sentence explains what something is (e.g., 'Embeddings are lists of numbers'), extract the subject as a Primitive.",
                "4. INTEGRATIONS: Look for third-party handoffs. If MotherDuck calls OpenAI, 'OpenAI API' is an Integration.",
                "5. NO GENERALIZATION: If the text says 'use CTAS to save money', extract 'CTAS' (Syntax) and 'Money/Cost' (Topic/Primitive).",
            ]
        )

        return "\n".join(rules)


class RelationshipType(str, Enum):
    DEFINES = "defines"
    IMPLEMENTS = "implements"
    REQUIRES = "requires"
    COMPARES_TO = "compares_to"
    IMPACTS = "impacts"
    EXTENDS = "extends"
    ASSOCIATED_WITH = "assoc"

    @classmethod
    def get_metadata(cls, rel_type: "RelationshipType") -> dict:
        metadata = {
            cls.DEFINES: {
                "desc": "The document provides the authoritative definition of an entity.",
                "trigger": "Sentences like 'X refers to...', 'X is...', or 'What is X?'",
                "pair": "(Document -> Primitive/Feature)",
            },
            cls.IMPLEMENTS: {
                "desc": "Technical code/syntax that performs a conceptual feature.",
                "trigger": "Using code to do a task (e.g., 'Use the embedding() function for semantic search').",
                "pair": "(Syntax -> Feature)",
            },
            cls.REQUIRES: {
                "desc": "A hard dependency, prerequisite, or limitation.",
                "trigger": "Words like 'needs', 'must have', 'depends on', or 'limited to'.",
                "pair": "(Feature/Syntax -> Primitive/Policy)",
            },
            cls.COMPARES_TO: {
                "desc": "A direct comparison between two similar methods or products.",
                "trigger": "Words like 'unlike', 'vs', 'better than', or 'alternative to'.",
                "pair": "(Feature/Product -> Feature/Product)",
            },
            cls.IMPACTS: {
                "desc": "How an action or syntax affects a non-entity topic like cost or speed.",
                "trigger": "Sentences about results: 'saves time', 'increases cost', 'improves performance'.",
                "pair": "(Syntax -> Topic/Efficiency)",
            },
            cls.EXTENDS: {
                "desc": "Building upon an existing codebase or product.",
                "trigger": "Words like 'built on', 'extension of', or 'compatible with'.",
                "pair": "(Product -> Product)",
            },
        }
        return metadata.get(
            rel_type,
            {"desc": "General association", "trigger": "Related context", "pair": "(Any -> Any)"},
        )

    @classmethod
    def get_extraction_rules(cls) -> str:
        rules = ["### RELATIONSHIP LOGIC (How to connect entities):"]
        for rt in cls:
            meta = cls.get_metadata(rt)
            rules.append(f"- **{rt.value}** {meta['pair']}: {meta['desc']}")
            rules.append(f"  * Detection Trigger: {meta['trigger']}")
        return "\n".join(rules)


class ClaimType(str, Enum):
    DEFINITION = "Definition"
    INSTRUCTION = "Instruction"
    PERFORMANCE = "Performance"
    VALUE_PROP = "Value Prop"

    @classmethod
    def get_metadata(cls, claim_type: "ClaimType") -> dict:
        metadata = {
            cls.DEFINITION: {
                "desc": "Foundational knowledge/Background context.",
                "goal": "Capture 'What is it?' to educate future users.",
                "example": "Embeddings are numerical vectors representing meaning.",
            },
            cls.INSTRUCTION: {
                "desc": "Mandatory implementation steps or policy rules.",
                "goal": "Capture 'How do I use it?' and 'What are the limits?'.",
                "example": "You must use the text-embedding-3-small model for this function.",
            },
            cls.PERFORMANCE: {
                "desc": "Operational optimization and cost/time efficiency.",
                "goal": "Capture 'How do I make it better/cheaper?'.",
                "example": "Use CTAS to store embeddings so you don't pay to re-generate them.",
            },
            cls.VALUE_PROP: {
                "desc": "Strategic advantages or unique selling points.",
                "goal": "Capture 'Why is this better than the alternative?'.",
                "example": "MotherDuck enables serverless vector search without a dedicated vector DB.",
            },
        }
        return metadata.get(claim_type, {})

    @classmethod
    def get_extraction_rules(cls) -> str:
        rules = ["### STRATEGIC CLAIM EXTRACTION (The 'Insights' Layer):"]
        for ct in cls:
            meta = cls.get_metadata(ct)
            rules.append(f"- **[{ct.value}]**: {meta['desc']}")
            rules.append(f"  * Primary Goal: {meta['goal']}")
            rules.append(f"  * Example: {meta['example']}")

        rules.append(
            "\nCRITICAL: Ignore marketing fluff (e.g., 'awesome', 'easy'). Focus on logic and mechanics."
        )
        return "\n".join(rules)
