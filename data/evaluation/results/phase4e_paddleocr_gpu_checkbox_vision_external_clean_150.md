# Phase4E Paddleocr Gpu Checkbox Vision External Clean 150

Field accuracy is the percentage of individual W-2 values that matched the known correct answer.
A document failure means the pipeline could not complete extraction for the document at all.
Failure inspection values are intended for synthetic evaluation data; future real-data reports should redact sensitive values.

## Summary

| Metric | Value |
| --- | ---: |
| Pipeline | pipeline_a |
| Dataset/source | Symage/synthetic-us-forms-preview |
| Document condition / variant scope | Clean render |
| Documents tested | 150 |
| Successful documents | 150 |
| Failed documents | 0 |
| Failure rate | 0.00% |
| Fields checked | 3,450 |
| Correct fields | 3,450 |
| Field accuracy | 100.00% |
| Average processing time per document | 1.439 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Box 13 retirement plan | `box_13.retirement_plan` | 150 | 0 | 100.00% |
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

No incorrect field results were recorded for this benchmark.

## Interpretation

No document-level failures were recorded in this benchmark.
These results do not establish production readiness by themselves.
