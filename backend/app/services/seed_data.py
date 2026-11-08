from typing import List, Dict, Any
from app.schemas.contracts import BrandRule, RuleCategory, Severity, ApprovedFact

DEMO_ORG_ID = "ORG-SAMPLE-DEMO-01"
DEMO_ORG_NAME = "Sample Demo Brand (AuroraGear — Fictional Evaluation Dataset)"
DEMO_BRAND_PALETTE: List[Dict[str, Any]] = [
    {
        "palette_id": "PAL-NAVY-001",
        "name": "Aurora Deep Navy",
        "hex": "#0F172A",
        "rgb": (15, 23, 42),
        "max_delta_e": 15.0,
        "document_id": "DOC-BRAND-CONSTITUTION-V1",
        "document_name": "Sample_Brand_Guidelines_v1.pdf",
        "verified_page_or_row": 6,
    },
    {
        "palette_id": "PAL-SLATE-002",
        "name": "Aurora Technical Slate",
        "hex": "#334155",
        "rgb": (51, 65, 85),
        "max_delta_e": 15.0,
        "document_id": "DOC-BRAND-CONSTITUTION-V1",
        "document_name": "Sample_Brand_Guidelines_v1.pdf",
        "verified_page_or_row": 6,
    },
    {
        "palette_id": "PAL-WHITE-003",
        "name": "Aurora Crisp White",
        "hex": "#FFFFFF",
        "rgb": (255, 255, 255),
        "max_delta_e": 12.0,
        "document_id": "DOC-BRAND-CONSTITUTION-V1",
        "document_name": "Sample_Brand_Guidelines_v1.pdf",
        "verified_page_or_row": 6,
    },
]


def get_demo_brand_palette() -> List[Dict[str, Any]]:
    return DEMO_BRAND_PALETTE


def get_demo_brand_rules() -> List[BrandRule]:
    return [
        BrandRule(
            rule_id="RULE-TERM-001",
            category=RuleCategory.BANNED_TERM,
            title="Prohibit absolute 'guaranteed' marketing claims",
            description="Never use the absolute term 'guaranteed' in promotional copy.",
            mandatory_flag=True,
            severity=Severity.HIGH,
            pattern_or_target="guaranteed",
            expected_replacement="tested",
            document_id="DOC-BRAND-CONSTITUTION-V1",
            document_name="Sample_Brand_Guidelines_v1.pdf",
            verified_page_or_row=4,
            version="1.0",
        ),
        BrandRule(
            rule_id="RULE-TERM-002",
            category=RuleCategory.BANNED_TERM,
            title="Prohibit unverifiable superlative 'world's #1'",
            description="Do not use 'world's #1' or '#1 in the world' in campaign text.",
            mandatory_flag=True,
            severity=Severity.HIGH,
            pattern_or_target="world's #1",
            expected_replacement="enterprise-grade",
            document_id="DOC-BRAND-CONSTITUTION-V1",
            document_name="Sample_Brand_Guidelines_v1.pdf",
            verified_page_or_row=5,
            version="1.0",
        ),
        BrandRule(
            rule_id="RULE-CASE-001",
            category=RuleCategory.BRAND_CASING,
            title="Exact Brand Casing for AURORAGEAR",
            description="The demonstration brand name must always be written in uppercase as AURORAGEAR.",
            mandatory_flag=True,
            severity=Severity.MEDIUM,
            pattern_or_target="AURORAGEAR",
            expected_replacement="AURORAGEAR",
            document_id="DOC-BRAND-CONSTITUTION-V1",
            document_name="Sample_Brand_Guidelines_v1.pdf",
            verified_page_or_row=2,
            version="1.0",
        ),
        BrandRule(
            rule_id="RULE-DISC-001",
            category=RuleCategory.MANDATORY_DISCLAIMER,
            title="Battery Claim Testing Qualification Notice",
            description="Any draft mentioning battery hours must include the phrase 'under specified laboratory testing conditions'.",
            mandatory_flag=True,
            severity=Severity.MEDIUM,
            pattern_or_target="under specified laboratory testing conditions",
            expected_replacement="under specified laboratory testing conditions",
            document_id="DOC-BRAND-CONSTITUTION-V1",
            document_name="Sample_Brand_Guidelines_v1.pdf",
            verified_page_or_row=9,
            version="1.0",
        ),
        BrandRule(
            rule_id="RULE-NUM-001",
            category=RuleCategory.NUMERIC_BOUND,
            title="Maximum Approved Discount Percentage Bound",
            description="Promotional discount claims must not exceed 30%.",
            mandatory_flag=True,
            severity=Severity.HIGH,
            pattern_or_target="discount_percent",
            numeric_max=30.0,
            numeric_unit="%",
            document_id="DOC-BRAND-CONSTITUTION-V1",
            document_name="Sample_Brand_Guidelines_v1.pdf",
            verified_page_or_row=12,
            version="1.0",
        ),
    ]


def get_demo_approved_facts() -> List[ApprovedFact]:
    return [
        ApprovedFact(
            fact_id="FACT-BAT-001",
            topic_key="battery_life",
            subject_keywords=["battery", "charge", "hours"],
            canonical_text="Up to 12 hours of battery life under specified laboratory testing conditions.",
            approved_numeric_value=12.0,
            numeric_unit="hours",
            comparator="up_to",
            required_conditions=["up to", "under specified laboratory testing conditions"],
            prohibited_overstatements=["guaranteed", "uninterrupted"],
            document_id="DOC-APPROVED-FACTS-V1",
            document_name="Sample_Approved_Facts_Vault_v1.csv",
            verified_page_or_row=2,
            version="1.0",
        ),
        ApprovedFact(
            fact_id="FACT-CHG-002",
            topic_key="fast_charging",
            subject_keywords=["fast charge", "charging", "minutes"],
            canonical_text="Up to 50% charge in 30 minutes under specified laboratory testing conditions.",
            approved_numeric_value=30.0,
            numeric_unit="minutes",
            comparator="up_to",
            required_conditions=["up to", "under specified laboratory testing conditions"],
            prohibited_overstatements=["instant", "guaranteed"],
            document_id="DOC-APPROVED-FACTS-V1",
            document_name="Sample_Approved_Facts_Vault_v1.csv",
            verified_page_or_row=3,
            version="1.0",
        ),
    ]


def get_demo_sample_drafts() -> List[Dict[str, Any]]:
    return [
        {
            "sample_id": "SAMPLE-CLEAN-01",
            "title": "Sample 1: Fully Compliant Product Announcement",
            "description": "Follows exact AURORAGEAR casing, supported 12-hour battery claim, and required testing conditions.",
            "blocks": [
                {
                    "document_block_id": "blk-p1",
                    "text": "AURORAGEAR introduces our latest portable workstation designed for field engineers.",
                },
                {
                    "document_block_id": "blk-p2",
                    "text": "Experience up to 12 hours of battery life under specified laboratory testing conditions during your workday.",
                },
            ],
        },
        {
            "sample_id": "SAMPLE-TERM-VIOLATION-02",
            "title": "Sample 2: Brand Casing & Banned Superlative Violation",
            "description": "Contains incorrect 'AuroraGear' casing and prohibited 'world's #1' superlative.",
            "blocks": [
                {
                    "document_block_id": "blk-p1",
                    "text": "AuroraGear is proud to release the world's #1 field notebook for modern teams.",
                }
            ],
        },
        {
            "sample_id": "SAMPLE-CLAIM-VIOLATION-03",
            "title": "Sample 3: Unqualified / Exaggerated Promotional Claim",
            "description": "Contains a 'guaranteed' battery claim without testing qualifiers and an unverified cosmic durability claim.",
            "blocks": [
                {
                    "document_block_id": "blk-p1",
                    "text": "AURORAGEAR delivers 12 hours of guaranteed battery life on a single charge!",
                },
                {
                    "document_block_id": "blk-p2",
                    "text": "Our chassis is certified to survive 5000 meters of deep-ocean pressure.",
                },
            ],
        },
    ]