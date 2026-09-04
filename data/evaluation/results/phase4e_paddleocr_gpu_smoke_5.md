# Phase4E Paddleocr Gpu Smoke 5

Field accuracy is the percentage of individual W-2 values that matched the known correct answer.
A document failure means the pipeline could not complete extraction for the document at all.
Failure inspection values are intended for synthetic evaluation data; future real-data reports should redact sensitive values.

## Summary

| Metric | Value |
| --- | ---: |
| Pipeline | pipeline_a |
| Dataset/source | Symage/synthetic-us-forms-preview |
| Document condition / variant scope | Clean render |
| Documents tested | 5 |
| Successful documents | 5 |
| Failed documents | 0 |
| Failure rate | 0.00% |
| Fields checked | 115 |
| Correct fields | 113 |
| Field accuracy | 98.26% |
| Average processing time per document | 2.114 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Box 13 retirement plan | `box_13.retirement_plan` | 3 | 2 | 60.00% |
| Box 13 statutory employee | `box_13.statutory_employee` | 5 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 5 | 0 | 100.00% |
| Employee first name | `employee.first_name` | 5 | 0 | 100.00% |
| Employee last name | `employee.last_name` | 5 | 0 | 100.00% |
| Employee middle initial | `employee.middle_initial` | 5 | 0 | 100.00% |
| Employee SSN | `employee.ssn` | 5 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 5 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 5 | 0 | 100.00% |
| Employer EIN | `employer.ein` | 5 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 5 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 5 | 0 | 100.00% |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 5 | 0 | 100.00% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 5 | 0 | 100.00% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 5 | 0 | 100.00% |
| Box 4 Social Security tax withheld | `federal_wages_and_taxes.box_4_social_security_tax_withheld` | 5 | 0 | 100.00% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 5 | 0 | 100.00% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 5 | 0 | 100.00% |
| Box 7 Social Security tips | `federal_wages_and_taxes.box_7_social_security_tips` | 5 | 0 | 100.00% |
| Box 8 allocated tips | `federal_wages_and_taxes.box_8_allocated_tips` | 5 | 0 | 100.00% |
| Document type | `metadata.document_type` | 5 | 0 | 100.00% |
| Schema version | `metadata.schema_version` | 5 | 0 | 100.00% |
| Tax year | `metadata.tax_year` | 5 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Box 13 retirement plan (`box_13.retirement_plan`) | 2 |

Showing all 2 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Box 13 retirement plan was the lowest-accuracy field at 60.00%.
These results do not establish production readiness by themselves.
