# Phase4E Tesseract Supplemental Psm11 Recovery Diagnostic 5

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
| Correct fields | 111 |
| Field accuracy | 96.52% |
| Average processing time per document | 3.640 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Employee first name | `employee.first_name` | 4 | 1 | 80.00% |
| Employee middle initial | `employee.middle_initial` | 4 | 1 | 80.00% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 4 | 1 | 80.00% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 4 | 1 | 80.00% |
| Box 13 retirement plan | `box_13.retirement_plan` | 5 | 0 | 100.00% |
| Box 13 statutory employee | `box_13.statutory_employee` | 5 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 5 | 0 | 100.00% |
| Employee last name | `employee.last_name` | 5 | 0 | 100.00% |
| Employee SSN | `employee.ssn` | 5 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 5 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 5 | 0 | 100.00% |
| Employer EIN | `employer.ein` | 5 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 5 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 5 | 0 | 100.00% |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 5 | 0 | 100.00% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 5 | 0 | 100.00% |
| Box 4 Social Security tax withheld | `federal_wages_and_taxes.box_4_social_security_tax_withheld` | 5 | 0 | 100.00% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 5 | 0 | 100.00% |
| Box 7 Social Security tips | `federal_wages_and_taxes.box_7_social_security_tips` | 5 | 0 | 100.00% |
| Box 8 allocated tips | `federal_wages_and_taxes.box_8_allocated_tips` | 5 | 0 | 100.00% |
| Document type | `metadata.document_type` | 5 | 0 | 100.00% |
| Schema version | `metadata.schema_version` | 5 | 0 | 100.00% |
| Tax year | `metadata.tax_year` | 5 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Employee first name (`employee.first_name`) | 1 |
| Employee middle initial (`employee.middle_initial`) | 1 |
| Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1 |
| Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1 |

Showing all 4 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900075-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 8.15E+4 | 81 | ocr |
| symage_900119-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Jeffrey | veffrey | ocr |
| symage_900119-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | A | `null` | ocr |
| symage_900123-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1294.85 | 1204.85 | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Employee first name was the lowest-accuracy field at 80.00%.
These results do not establish production readiness by themselves.
