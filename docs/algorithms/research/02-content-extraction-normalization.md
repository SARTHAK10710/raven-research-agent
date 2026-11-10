# Phase 6.7 — Research Content Extraction & Fact Normalization

**Project:** Raven Research Agent  
**Phase:** 6 — Algorithms & Processing Design  
**Subphase:** 6.7 — Research Content Extraction & Fact Normalization  
**Status:** Architecture and algorithm specification  
**Optimization Priority:** Quality first  
**Processing Approach:** Hybrid — deterministic rules, conventional NLP/statistical methods, and selective non-generative ML

---

## 1. Purpose

The Research Engine discovers sources, but discovered sources are not yet structured research findings.

A webpage, PDF, technical document, report, or dataset may contain:

- Relevant facts.
- Claims and opinions.
- Numerical information.
- Dates and timelines.
- Entity relationships.
- Tables and structured records.
- Contradictory statements.
- Missing or incomplete information.

Raven must transform this content into structured, traceable information without losing its original meaning or context.

This phase defines the algorithms responsible for:

1. Retrieving source content.
2. Extracting readable content.
3. Parsing different document formats.
4. Normalizing extracted content.
5. Extracting facts and claims.
6. Normalizing entities and attributes.
7. Preserving temporal and contextual meaning.
8. Linking findings to source evidence.
9. Validating extraction quality.

### Core principles

1. Original source content must remain distinguishable from extracted content.
2. Every extracted finding must retain source provenance.
3. Extraction must preserve meaning, qualifiers, units, and temporal context.
4. Claims must not automatically be treated as verified facts.
5. Missing information must not be fabricated.
6. Tables and structured data must retain their original relationships.
7. Uncertain extraction results must remain uncertain.
8. Duplicate content must not be mistaken for independent evidence.
9. External content must be treated as untrusted input.
10. Quality takes priority over extraction speed.

---

# 2. Algorithm Inventory

This document defines nine algorithms.

| ID | Algorithm | Primary responsibility |
|---|---|---|
| 6.7.1 | Source Retrieval & Accessibility | Retrieve source content safely |
| 6.7.2 | Document Format Detection & Parsing | Identify and parse source formats |
| 6.7.3 | Content Extraction & Structural Preservation | Extract useful content while retaining structure |
| 6.7.4 | Content Cleaning & Normalization | Normalize extracted content |
| 6.7.5 | Fact & Claim Extraction | Identify candidate facts and claims |
| 6.7.6 | Entity & Attribute Normalization | Normalize entities and attributes |
| 6.7.7 | Temporal & Contextual Normalization | Preserve dates, units, and contextual meaning |
| 6.7.8 | Evidence Linking & Provenance Assignment | Connect findings to source evidence |
| 6.7.9 | Extraction Quality Validation | Validate extraction completeness and correctness |

---

# 3. 6.7.1 — Source Retrieval & Accessibility

## Purpose

Retrieve content from discovered candidate sources.

A source may be publicly accessible, restricted, temporarily unavailable, or available only in a supported downloadable format.

Retrieval must establish whether the content was actually obtained before downstream extraction begins.

## Supported source categories

The architecture should support extensible source adapters for:

- Webpages.
- HTML documents.
- PDF documents.
- DOCX documents.
- TXT files.
- CSV files.
- Structured datasets.
- Other explicitly supported document formats.

Actual supported formats depend on the adapters implemented later.

## Retrieval metadata

Capture:

- Source reference.
- Source URL or identifier.
- Retrieval timestamp.
- HTTP or adapter response status.
- Content type.
- Content length.
- Redirect information.
- Retrieval method.
- Accessibility status.
- Content checksum where supported.

## Retrieval outcomes

- `RETRIEVED`
- `PARTIALLY_RETRIEVED`
- `INACCESSIBLE`
- `UNSUPPORTED`
- `RESTRICTED`
- `TIMEOUT`
- `FAILED`
- `PENDING`

## Algorithm

**Input:**

- Candidate source record.
- Retrieval configuration.
- Access policy.
- Execution context.

**Output:**

- Retrieved content reference.
- Retrieval metadata.
- Accessibility status.
- Failure information, if applicable.

### Processing steps

1. Load the candidate source.
2. Validate the source reference.
3. Validate access permissions and retrieval policy.
4. Determine the appropriate retrieval adapter.
5. Retrieve the source within configured limits.
6. Validate the response status.
7. Capture redirects and final location.
8. Inspect content type and size.
9. Store retrieved content in the appropriate content-storage layer.
10. Generate a content checksum where supported.
11. Record retrieval metadata.
12. Return the retrieval result.

### Pseudocode

```text
FUNCTION retrieve_source(source):

    validate_source_reference(source)

    validate_retrieval_permissions(source)

    adapter = select_retrieval_adapter(source)

    IF adapter == NONE:
        RETURN UNSUPPORTED

    response = adapter.retrieve(source)

    IF response.timeout:
        RETURN TIMEOUT

    IF response.access_denied:
        RETURN RESTRICTED

    IF NOT response.success:
        RETURN FAILED

    validate_content_type(response)

    validate_content_size(response)

    content_reference = store_retrieved_content(response)

    metadata = capture_retrieval_metadata(response)

    RETURN {
        content_reference,
        metadata,
        retrieval_status
    }
```

## Retrieval safeguards

- Apply request timeouts and size limits.
- Respect access restrictions and configured crawling policies.
- Do not attempt to bypass authentication or access controls.
- Validate redirects and destination URLs.
- Protect against unsafe local-network or internal-resource access.
- Treat retrieved content as untrusted.
- Avoid executing scripts or active content.
- Do not claim successful retrieval when only a search snippet is available.
- Preserve the distinction between publication time and retrieval time.

---

# 4. 6.7.2 — Document Format Detection & Parsing

## Purpose

Identify the format of retrieved content and select the appropriate parser.

Different formats require different extraction techniques.

A PDF, for example, may contain selectable text, scanned images, tables, or a combination of these.

## Format detection signals

- Declared content type.
- File extension.
- File signature or magic bytes.
- Document structure.
- Parser compatibility.
- Actual content inspection.

The declared content type or filename alone must not be treated as definitive proof of format.

## Parsing categories

| Format | Parsing approach |
|---|---|
| HTML | DOM-based parsing |
| PDF | Text and structural extraction |
| DOCX | Document structure parsing |
| TXT | Text decoding and normalization |
| CSV | Delimited record parsing |
| Structured datasets | Format-specific schema parsing |

OCR may be introduced as a separately configured capability for scanned documents. It must not be assumed to be available merely because PDF support exists.

## Algorithm

**Input:**

- Retrieved content reference.
- Content metadata.
- Supported parser registry.

**Output:**

- Detected format.
- Parsed document representation.
- Parsing status.
- Unsupported or malformed content details.

### Processing steps

1. Load retrieved content.
2. Inspect file signature and metadata.
3. Determine the actual content format.
4. Select a compatible parser.
5. Validate document integrity.
6. Parse the content.
7. Preserve document hierarchy and structural elements.
8. Detect parsing failures and unsupported features.
9. Record parser version and processing metadata.
10. Return the parsed representation.

### Pseudocode

```text
FUNCTION parse_document(content):

    format = detect_actual_format(content)

    parser = get_compatible_parser(format)

    IF parser == NONE:
        RETURN UNSUPPORTED_FORMAT

    integrity = validate_document_integrity(content)

    IF NOT integrity.valid:
        RETURN INVALID_DOCUMENT

    parsed = parser.parse(content)

    IF parsed.is_partial:
        status = PARTIALLY_PARSED
    ELSE:
        status = PARSED

    RETURN {
        format,
        parsed_document,
        parser_version,
        status
    }
```

## Parsing safeguards

- Preserve page boundaries where available.
- Preserve headings and section hierarchy.
- Preserve table rows and columns.
- Preserve document ordering.
- Record missing or malformed sections.
- Do not silently discard unsupported content.
- Distinguish empty documents from parser failures.
- Preserve the original retrieved content separately.

---

# 5. 6.7.3 — Content Extraction & Structural Preservation

## Purpose

Extract relevant readable content from parsed documents while retaining the relationships and structure that give it meaning.

Simply converting an entire document into one long text string can destroy important information.

For example, a table may contain product names, prices, currencies, and billing periods. Flattening the table can make the values ambiguous.

## Content types

Extract:

- Titles.
- Headings.
- Paragraphs.
- Lists.
- Tables.
- Captions.
- Footnotes.
- Metadata.
- Dates.
- Links.
- Structured records.
- Relevant document sections.

## Structural representation

The extracted document should retain:

- Document identity.
- Section hierarchy.
- Content block identity.
- Block type.
- Ordering.
- Page or location reference.
- Parent-child relationships.
- Table structure.
- Original text.

## Algorithm

**Input:**

- Parsed document.
- Document structure.
- Extraction configuration.

**Output:**

- Structured content blocks.
- Section hierarchy.
- Table representations.
- Location references.

### Processing steps

1. Load the parsed document.
2. Identify document sections.
3. Identify headings and hierarchy.
4. Extract paragraphs and lists.
5. Extract tables while preserving row-column relationships.
6. Extract captions and footnotes.
7. Preserve hyperlinks and source locations.
8. Assign stable content block references.
9. Preserve ordering.
10. Record extraction completeness.

### Pseudocode

```text
FUNCTION extract_structured_content(document):

    sections = identify_sections(document)

    blocks = []

    FOR EACH section IN sections:

        headings = extract_headings(section)

        paragraphs = extract_paragraphs(section)

        lists = extract_lists(section)

        tables = extract_tables(section)

        metadata = extract_section_metadata(section)

        structured_blocks = preserve_structure(
            headings,
            paragraphs,
            lists,
            tables,
            metadata
        )

        blocks.append(structured_blocks)

    RETURN {
        blocks,
        section_hierarchy,
        extraction_status
    }
```

## Structural safeguards

- Do not merge unrelated paragraphs.
- Do not detach footnotes from the content they qualify.
- Preserve table headers and units.
- Preserve section context for every extracted block.
- Preserve original wording.
- Distinguish captions from main content.
- Avoid interpreting navigation elements as substantive findings.

---

# 6. 6.7.4 — Content Cleaning & Normalization

## Purpose

Clean extracted content and create a consistent representation for downstream fact extraction.

Cleaning must remove irrelevant formatting noise without changing the underlying meaning.

## Normalization operations

- Unicode normalization.
- Whitespace normalization.
- Line-break normalization.
- Encoding correction where unambiguous.
- HTML entity decoding.
- Removal of irrelevant navigation and boilerplate.
- Repeated header/footer identification.
- Text segmentation.
- Consistent representation of metadata.

## Important distinction

Maintain two representations:

1. **Original extracted content:** Preserves what was obtained from the source.
2. **Normalized content:** Used for processing and analysis.

Never overwrite the original extracted content with a cleaned version.

## Algorithm

**Input:**

- Structured content blocks.
- Original source references.
- Cleaning rules.

**Output:**

- Normalized content blocks.
- Cleaning metadata.
- Links to original blocks.

### Processing steps

1. Load structured content.
2. Preserve original content references.
3. Normalize encoding and Unicode.
4. Normalize whitespace and line breaks.
5. Identify irrelevant boilerplate.
6. Remove only content that can be safely classified as irrelevant.
7. Preserve meaningful qualifiers and punctuation.
8. Normalize metadata representation.
9. Link normalized blocks to original blocks.
10. Validate semantic preservation.

### Pseudocode

```text
FUNCTION normalize_content(blocks):

    normalized_blocks = []

    FOR EACH block IN blocks:

        original = preserve_original_reference(block)

        content = normalize_unicode(block.content)

        content = normalize_whitespace(content)

        content = identify_boilerplate(content)

        IF boilerplate_removal_is_safe(content):
            content = remove_boilerplate(content)

        validate_meaning_preservation(
            block.content,
            content
        )

        normalized_blocks.append(
            create_normalized_block(
                content,
                original
            )
        )

    RETURN normalized_blocks
```

## Cleaning safeguards

- Preserve negation.
- Preserve uncertainty expressions.
- Preserve units and numerical values.
- Preserve quotations and attribution.
- Preserve date and time expressions.
- Do not remove meaningful legal or technical qualifications.
- Do not convert opinions into facts.
- Do not remove content merely because it is repeated in a document.

---

# 7. 6.7.5 — Fact & Claim Extraction

## Purpose

Identify candidate facts, claims, statements, and relationships within normalized source content.

This algorithm produces candidate research findings. It does not establish their truth.

## Candidate information categories

| Category | Description |
|---|---|
| `FACT_CLAIM` | A statement presented as factual |
| `OPINION` | A subjective judgment |
| `PREDICTION` | A statement about a possible future outcome |
| `ESTIMATE` | An approximate or calculated value |
| `STATISTIC` | A numerical or quantitative claim |
| `EVENT` | A statement describing an occurrence |
| `RELATIONSHIP` | A relationship between entities |
| `DEFINITION` | A description of a concept |
| `QUESTION` | An interrogative statement |
| `UNCLASSIFIED` | A statement that cannot be reliably categorized |

The category describes the nature of the source statement, not whether it is correct.

## Extraction methods

Use a hybrid approach:

- Rule-based sentence segmentation.
- Conventional NLP.
- Named entity recognition.
- Part-of-speech and dependency features.
- Pattern-based extraction.
- Statistical classifiers.
- Selective non-generative ML.

No generative LLM API or locally hosted generative LLM is part of this algorithm.

## Fact representation

A candidate finding should capture:

- Subject.
- Predicate or relationship.
- Object or value.
- Original statement.
- Source reference.
- Content block reference.
- Entity mentions.
- Qualifiers.
- Temporal context.
- Classification.
- Extraction confidence.

Not every statement can be represented as a complete subject-predicate-object structure. Incomplete findings must retain their original statement and be marked accordingly.

## Algorithm

**Input:**

- Normalized content blocks.
- Document structure.
- Source metadata.
- Entity extraction signals.

**Output:**

- Candidate facts and claims.
- Classification metadata.
- Original text references.
- Extraction confidence.

### Processing steps

1. Segment content into meaningful units.
2. Identify sentence boundaries.
3. Extract entity mentions.
4. Identify candidate predicates and attributes.
5. Detect numerical and temporal expressions.
6. Classify statement type.
7. Preserve negation and qualifiers.
8. Generate structured candidate findings.
9. Link findings to original text.
10. Assign extraction confidence.
11. Mark incomplete or ambiguous findings.

### Pseudocode

```text
FUNCTION extract_candidate_findings(content_blocks):

    findings = []

    FOR EACH block IN content_blocks:

        segments = segment_content(block)

        FOR EACH segment IN segments:

            entities = extract_entity_mentions(segment)

            predicates = identify_predicates(segment)

            values = extract_candidate_values(segment)

            qualifiers = extract_qualifiers(segment)

            classification = classify_statement(segment)

            finding = build_candidate_finding(
                segment,
                entities,
                predicates,
                values,
                qualifiers,
                classification
            )

            finding.confidence = evaluate_extraction_confidence(
                finding
            )

            findings.append(finding)

    RETURN findings
```

## Critical safeguards

The extraction process must preserve the difference between:

- A source asserting something.
- A source quoting someone else.
- A source expressing an opinion.
- A source proposing a hypothetical.
- A source making a prediction.
- A source reporting an estimate.
- A source asking a question.

For example:

"The company may launch the product next year."

This must not become:

"The company will launch the product next year."

Similarly:

"Analysts estimate revenue at approximately $10 million."

Must preserve both the attribution and the uncertainty of the estimate.

---

# 8. 6.7.6 — Entity & Attribute Normalization

## Purpose

Normalize extracted entity mentions and attributes into consistent structured representations.

The same entity may be referenced using:

- Full name.
- Short name.
- Abbreviation.
- Product name.
- Brand name.
- Alias.
- Alternative spelling.

Likewise, attributes may be expressed using different wording.

Normalization makes research findings easier to compare and retrieve.

## Entity normalization

Entity types may include:

- Organizations.
- People.
- Products.
- Services.
- Technologies.
- Locations.
- Events.
- Concepts.
- Other identifiable entities.

## Attribute normalization

Examples:

| Source wording | Normalized attribute |
|---|---|
| Annual recurring revenue | `annual_recurring_revenue` |
| ARR | `annual_recurring_revenue` |
| Monthly active users | `monthly_active_users` |
| MAU | `monthly_active_users` |
| Headquarters | `headquarters_location` |

The original wording must remain available.

## Algorithm

**Input:**

- Candidate findings.
- Entity mentions.
- Attribute expressions.
- Existing entity references.
- Entity and attribute normalization rules.

**Output:**

- Normalized entity references.
- Canonical attribute identifiers.
- Unresolved mentions.
- Normalization confidence.

### Processing steps

1. Extract entity mentions from candidate findings.
2. Normalize spelling and formatting.
3. Generate potential canonical entity matches.
4. Compare entity type and contextual attributes.
5. Evaluate aliases and identifiers.
6. Resolve only sufficiently supported matches.
7. Preserve unresolved mentions.
8. Map attributes to canonical identifiers.
9. Preserve original attribute wording.
10. Record normalization provenance.

### Pseudocode

```text
FUNCTION normalize_entities_and_attributes(findings):

    FOR EACH finding IN findings:

        FOR EACH mention IN finding.entity_mentions:

            candidates = find_entity_candidates(mention)

            match = evaluate_entity_match(
                mention,
                candidates,
                finding.context
            )

            IF match.is_sufficient:
                attach_canonical_entity(match.entity)
            ELSE:
                preserve_unresolved_mention(mention)

        FOR EACH attribute IN finding.attributes:

            normalized = map_attribute_to_canonical_form(
                attribute
            )

            preserve_original_attribute(attribute)

            attach_normalized_attribute(normalized)

    RETURN normalized_findings
```

## Safeguards

- Similar names do not establish entity identity.
- Entity matching must consider type and context.
- Ambiguous entity matches must remain unresolved.
- Do not merge unrelated organizations or products.
- Preserve the original entity mention.
- Attribute normalization must not remove distinctions between different metrics.
- Do not treat similar abbreviations as equivalent without contextual validation.

---

# 9. 6.7.7 — Temporal & Contextual Normalization

## Purpose

Preserve the time, location, units, conditions, and scope associated with extracted findings.

A number without context can be misleading.

For example:

"Revenue is 10 million."

This is incomplete without knowing:

- Currency.
- Reporting period.
- Revenue definition.
- Entity.
- Whether it is actual or estimated.
- Whether it is historical or current.

## Context dimensions

### A. Temporal context

- Publication date.
- Event date.
- Effective date.
- Reporting period.
- Valid-from date.
- Valid-until date.
- Historical reference period.

### B. Geographic context

- Country.
- State or region.
- City.
- Market.
- Geographic scope.

### C. Measurement context

- Value.
- Unit.
- Currency.
- Scale.
- Measurement period.
- Metric definition.

### D. Qualification context

- Actual versus estimated.
- Minimum or maximum.
- Approximate value.
- Conditional statement.
- Forecast.
- Reported versus independently measured.

## Algorithm

**Input:**

- Candidate findings.
- Temporal expressions.
- Numerical expressions.
- Entity references.
- Source context.

**Output:**

- Context-enriched findings.
- Normalized temporal fields.
- Normalized measurement fields.
- Unresolved context indicators.

### Processing steps

1. Identify dates and time expressions.
2. Determine whether dates refer to publication, events, or reporting periods.
3. Normalize dates where unambiguous.
4. Extract numerical values.
5. Identify units and currencies.
6. Identify geographic scope.
7. Identify conditions and qualifiers.
8. Preserve original expressions.
9. Validate measurement compatibility.
10. Mark missing or ambiguous context.

### Pseudocode

```text
FUNCTION normalize_temporal_context(finding):

    temporal = extract_temporal_expressions(finding)

    measurements = extract_measurements(finding)

    geography = extract_geographic_context(finding)

    qualifiers = extract_qualifiers(finding)

    normalized_temporal = normalize_dates(temporal)

    normalized_measurements = normalize_units(
        measurements
    )

    validate_context_compatibility(
        normalized_temporal,
        normalized_measurements,
        geography
    )

    RETURN enrich_finding_context(
        finding,
        normalized_temporal,
        normalized_measurements,
        geography,
        qualifiers
    )
```

## Temporal safeguards

- Do not confuse publication date with event date.
- Do not assume an undated claim is current.
- Preserve historical reporting periods.
- Distinguish forecast periods from actual periods.
- Preserve timezone information where relevant.
- Do not infer a missing date without evidence.

## Measurement safeguards

- Never compare incompatible currencies without an explicit conversion basis.
- Preserve original units.
- Distinguish monthly from annual metrics.
- Distinguish users from active users.
- Distinguish actual values from estimates.
- Do not silently convert incompatible metric definitions.

---

# 10. 6.7.8 — Evidence Linking & Provenance Assignment

## Purpose

Connect every candidate finding to the precise source material from which it was extracted.

Evidence linking makes research traceable and allows downstream verification.

A finding without traceable evidence must not be treated as a fully supported research result.

## Evidence references

Where available, preserve:

- Source record ID.
- Source URL or identifier.
- Retrieved content reference.
- Document ID.
- Page number.
- Section heading.
- Content block ID.
- Text span or offset.
- Original excerpt.
- Publication timestamp.
- Retrieval timestamp.
- Extraction method.
- Parser version.

## Provenance chain

The intended relationship is:

```text
Source
  |
  v
Retrieved Content
  |
  v
Parsed Document
  |
  v
Extracted Content Block
  |
  v
Candidate Finding
  |
  v
Evidence Record
```

Each stage must retain references to its upstream source.

## Algorithm

**Input:**

- Candidate findings.
- Extracted content blocks.
- Source metadata.
- Document location references.

**Output:**

- Evidence-linked findings.
- Evidence records.
- Provenance metadata.
- Evidence completeness status.

### Processing steps

1. Retrieve the original content block for each finding.
2. Resolve the originating document.
3. Resolve the source record.
4. Capture the exact supporting excerpt.
5. Capture page, section, or text location where available.
6. Link the finding to its evidence record.
7. Record extraction method and processing version.
8. Validate that the excerpt supports the extracted finding.
9. Mark incomplete evidence links.
10. Return evidence-linked findings.

### Pseudocode

```text
FUNCTION assign_evidence_provenance(findings):

    FOR EACH finding IN findings:

        block = resolve_originating_content_block(
            finding
        )

        source = resolve_source_reference(block)

        IF block == NONE OR source == NONE:
            mark_evidence_incomplete(finding)
            continue

        excerpt = extract_supporting_excerpt(
            finding,
            block
        )

        evidence = create_evidence_record(
            source,
            block,
            excerpt
        )

        validate_evidence_alignment(
            finding,
            evidence
        )

        attach_evidence(finding, evidence)

    RETURN findings
```

## Evidence integrity rules

- Evidence must point to the actual source content.
- Do not create excerpts that change the meaning of the original statement.
- Preserve attribution and qualifiers.
- Distinguish primary evidence from secondary reporting.
- Preserve multiple evidence records when multiple sources support a finding.
- Do not count copied publications as independent corroboration.
- Missing evidence must be explicitly represented.
- Evidence extraction does not itself establish source reliability.

---

# 11. 6.7.9 — Extraction Quality Validation

## Purpose

Validate that extracted findings accurately represent the source content and contain sufficient context and provenance.

This is the final quality gate before candidate findings are passed to downstream research evaluation and verification.

## Validation dimensions

### A. Structural validation

- Required fields are present.
- Record references are valid.
- Entity and attribute structures are valid.
- Evidence links resolve correctly.

### B. Semantic validation

- Extracted statement matches the source.
- Negation is preserved.
- Attribution is preserved.
- Qualifiers are preserved.
- Numerical values are consistent.
- Context is not lost.

### C. Context validation

- Time period is preserved.
- Units are preserved.
- Currency is preserved.
- Geographic context is preserved.
- Actual and estimated values remain distinct.

### D. Provenance validation

- Source reference exists.
- Content block reference exists.
- Supporting excerpt is available.
- Extraction method is recorded.

## Validation outcomes

- `VALID`
- `VALID_WITH_WARNINGS`
- `INCOMPLETE`
- `NEEDS_REVIEW`
- `REJECTED`

## Algorithm

**Input:**

- Candidate findings.
- Evidence records.
- Normalized entities and attributes.
- Context metadata.
- Validation rules.

**Output:**

- Validated findings.
- Validation status.
- Warnings.
- Rejection reasons.

### Processing steps

1. Validate record structure.
2. Validate source and content references.
3. Compare the finding with its original excerpt.
4. Check preservation of negation and attribution.
5. Validate numerical values and units.
6. Validate temporal and geographic context.
7. Check for unsupported information.
8. Check for ambiguous entity resolution.
9. Assign a validation status.
10. Return accepted findings and review requirements.

### Pseudocode

```text
FUNCTION validate_extracted_findings(findings):

    results = []

    FOR EACH finding IN findings:

        structural = validate_structure(finding)

        provenance = validate_provenance(finding)

        semantic = validate_semantic_alignment(finding)

        context = validate_context(finding)

        IF NOT structural.valid:
            finding.status = REJECTED

        ELSE IF NOT provenance.valid:
            finding.status = INCOMPLETE

        ELSE IF semantic.has_material_error:
            finding.status = REJECTED

        ELSE IF context.has_ambiguity:
            finding.status = NEEDS_REVIEW

        ELSE IF has_non_critical_warnings(finding):
            finding.status = VALID_WITH_WARNINGS

        ELSE:
            finding.status = VALID

        results.append(finding)

    RETURN results
```

## Critical restriction

A finding marked `VALID` means its extraction is structurally and semantically acceptable relative to the source.

It does **not** mean that the underlying claim has been independently verified.

Source reliability, corroboration, contradiction analysis, and factual verification belong to the next Research Engine algorithm group.

---

# 12. Research Finding Data Contract

The following is a conceptual contract for extracted research findings.

```text
ResearchFinding:
    finding_id
    research_session_id
    snapshot_id
    source_id
    subject_entity_reference
    predicate
    object_value
    original_statement
    normalized_statement
    finding_type
    attributes
    temporal_context
    geographic_context
    measurement_context
    qualifiers
    extraction_confidence
    evidence_references
    extraction_status
    validation_status
    processing_version
    created_at
```

This is a logical contract, not a finalized database schema.

Evidence records remain independently identifiable and may be associated with multiple findings where appropriate.

---

# 13. Failure Handling

| Failure | Expected handling |
|---|---|
| Source unavailable | Record retrieval failure and try alternatives |
| Unsupported format | Mark unsupported and preserve source reference |
| Malformed document | Reject or mark partial parsing |
| Scanned PDF without OCR capability | Mark extraction limitation |
| Partial webpage content | Preserve partial retrieval status |
| Table parsing failure | Preserve original content and flag incomplete extraction |
| Encoding issue | Attempt safe normalization or mark failure |
| Ambiguous entity | Preserve unresolved mention |
| Missing measurement unit | Retain value with incomplete context |
| Missing publication date | Mark date unknown |
| Evidence location unavailable | Preserve source-level reference and mark incomplete location |
| Semantic extraction mismatch | Reject or request review |
| Duplicate source content | Preserve source identity and deduplicate appropriately |

Partial extraction is valid when its limitations are explicitly represented.

The system must not claim that an entire document was successfully processed when only part of it was extracted.

---

# 14. Security & Privacy Requirements

1. Treat all external source content as untrusted.
2. Never execute active content from retrieved documents.
3. Validate file types and content sizes.
4. Apply retrieval and parsing resource limits.
5. Prevent unauthorized access to internal network resources.
6. Preserve source and user execution boundaries.
7. Avoid logging unnecessary sensitive content.
8. Maintain provenance for every extracted finding.
9. Do not allow instructions embedded in source material to override system policies.
10. Keep original and normalized content under their defined access and retention policies.

---

# 15. Evaluation Metrics

These metrics will be evaluated during Phase 12.

| Area | Metric |
|---|---|
| Retrieval | Successful retrieval rate |
| Retrieval | Partial retrieval detection accuracy |
| Parsing | Format detection accuracy |
| Parsing | Parsing completeness |
| Structure | Table extraction accuracy |
| Cleaning | Semantic preservation accuracy |
| Fact extraction | Precision and recall |
| Classification | Statement classification accuracy |
| Entity normalization | Entity resolution accuracy |
| Attribute normalization | Attribute mapping accuracy |
| Context | Temporal normalization accuracy |
| Context | Measurement normalization accuracy |
| Provenance | Evidence-link completeness |
| Validation | Extraction error detection rate |
| Reliability | Partial extraction reporting accuracy |

Numerical targets will be defined during Phase 12.

---

# 16. Dependencies

This phase depends on:

- Phase 3 — Research Engine Architecture.
- Phase 5.3 — Core Entities & Relationships.
- Phase 5.5 — Research Engine Data Models.
- Phase 6.1 — Shared Algorithm Framework.
- Phase 6.6 — Query Understanding & Information Discovery.

---

# 17. Phase 6.7 Completion Criteria

The specification is complete when:

- Sources can be retrieved with explicit accessibility status.
- Supported document formats can be identified and parsed.
- Document structure is preserved.
- Extracted content is normalized without destroying the original.
- Facts and claims can be extracted as candidate findings.
- Entities and attributes can be normalized.
- Temporal and measurement context is preserved.
- Findings retain evidence and provenance.
- Extraction quality is validated.
- Partial extraction and uncertainty are represented explicitly.
- Security and privacy requirements are defined.

**Completion status:** Specification complete when documented and reviewed. Parser implementation, extraction model selection, accuracy calibration, and testing remain future work.

---

# 18. Next Algorithm Group

**Phase 6.8 — Research Source Evaluation & Verification**

The next document will define:

1. Source reliability evaluation.
2. Evidence quality assessment.
3. Independent corroboration.
4. Claim verification.
5. Contradiction detection.
6. Temporal consistency checks.
7. Confidence assessment.
8. Verification depth selection.
9. Final research finding qualification.

Phase 6.7 produces structured candidate findings with evidence references. Phase 6.8 determines how much confidence Raven should place in those findings.

**Important:** This document specifies intended processing behavior. It does not claim that retrieval adapters, parsers, OCR, extraction models, or validation systems have been implemented.
