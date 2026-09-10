# LM-Screen Context-Aware Deterministic Rule Engine

## Overview
The rule engine evaluates extracted statutory declarations against versioned YAML rule profiles. It operates deterministically and independently of LLM reasoning.

## Rule Profile Schema
```yaml
rule_id: LM001
version: 2026.1
name: MRP Declaration Screening
category: common
applicability:
  package_type: retail
required_declarations:
  - mrp
checks:
  - check: field_present
    failure_status: POTENTIAL_NON_COMPLIANCE
  - check: valid_format
    failure_status: POTENTIAL_NON_COMPLIANCE
legal_reference: "Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(e)"
status: ACTIVE
```

## Evaluated Rules
- `LM001`: MRP Declaration
- `LM002`: Net Quantity Statement
- `LM003`: Manufacturer / Packer / Importer Name & Address
- `LM004`: Date of Manufacture / Packing / Import
- `LM005`: Consumer Care Details
- `LM006`: Country of Origin (for imported goods)
- `LM008`: Font & Height Screening (approximate)
- `LM009`: GSTIN / GTIN Consistency Screening
