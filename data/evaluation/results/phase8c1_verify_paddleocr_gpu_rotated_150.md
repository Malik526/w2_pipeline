# Phase8C1 Verify Paddleocr Gpu Rotated 150

Field accuracy is the percentage of individual W-2 values that matched the known correct answer.
A document failure means the pipeline could not complete extraction for the document at all.
Failure inspection values are intended for synthetic evaluation data; future real-data reports should redact sensitive values.

## Summary

| Metric | Value |
| --- | ---: |
| Pipeline | pipeline_a |
| Dataset/source | Symage/synthetic-us-forms-preview |
| Document condition / variant scope | Rotated |
| Documents tested | 150 |
| Successful documents | 150 |
| Failed documents | 0 |
| Failure rate | 0.00% |
| Fields checked | 3,600 |
| Correct fields | 3,536 |
| Field accuracy | 98.22% |
| Average processing time per document | 1.423 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Box 13 retirement plan | `box_13.retirement_plan` | 90 | 60 | 60.00% |
| Employer name | `employer.name` | 146 | 4 | 97.33% |
| Box 13 statutory employee | `box_13.statutory_employee` | 150 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 150 | 0 | 100.00% |
| Employee first name | `employee.first_name` | 150 | 0 | 100.00% |
| Employee last name | `employee.last_name` | 150 | 0 | 100.00% |
| Employee middle initial | `employee.middle_initial` | 150 | 0 | 100.00% |
| Employee SSN | `employee.ssn` | 150 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 150 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 150 | 0 | 100.00% |
| Employer EIN | `employer.ein` | 150 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 150 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 150 | 0 | 100.00% |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 150 | 0 | 100.00% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 150 | 0 | 100.00% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 150 | 0 | 100.00% |
| Box 4 Social Security tax withheld | `federal_wages_and_taxes.box_4_social_security_tax_withheld` | 150 | 0 | 100.00% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 150 | 0 | 100.00% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 150 | 0 | 100.00% |
| Box 7 Social Security tips | `federal_wages_and_taxes.box_7_social_security_tips` | 150 | 0 | 100.00% |
| Box 8 allocated tips | `federal_wages_and_taxes.box_8_allocated_tips` | 150 | 0 | 100.00% |
| Document type | `metadata.document_type` | 150 | 0 | 100.00% |
| Schema version | `metadata.schema_version` | 150 | 0 | 100.00% |
| Tax year | `metadata.tax_year` | 150 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Box 13 retirement plan (`box_13.retirement_plan`) | 60 |
| Employer name (`employer.name`) | 4 |

Showing all 64 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Elan Consulting Corp | Elan Consulting Corp 2861 Geneva Ponce De Leon Rd | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Bespoke Designs LLC | Bespoke Designs LLC 6878 Normandy Tullahoma Rd | ocr |
| symage_900052-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900055-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900061-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900063-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900069-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900070-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900073-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900074-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900075-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900076-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900079-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900080-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900081-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | FutureReady Services | FutureReady Services 875 Francis Case Memorial Brg | ocr |
| symage_900083-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900085-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900088-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900091-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900094-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900095-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900096-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900098-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900099-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900103-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900108-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900109-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900113-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900115-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900117-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900118-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900120-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900127-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900129-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900130-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900131-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900133-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900138-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900142-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900143-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900145-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Global Insights Corp | Global Insights Corp 4522 Eastern Transportation Corridor | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Box 13 retirement plan was the lowest-accuracy field at 60.00%.
These results do not establish production readiness by themselves.
