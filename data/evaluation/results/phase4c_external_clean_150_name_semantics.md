# Phase4C External Clean 150 Name Semantics

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
| Correct fields | 3,420 |
| Field accuracy | 99.13% |
| Average processing time per document | 2.052 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Employee first name | `employee.first_name` | 140 | 10 | 93.33% |
| Employee middle initial | `employee.middle_initial` | 141 | 9 | 94.00% |
| Box 13 retirement plan | `box_13.retirement_plan` | 145 | 5 | 96.67% |
| Employer EIN | `employer.ein` | 148 | 2 | 98.67% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 148 | 2 | 98.67% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 149 | 1 | 99.33% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 149 | 1 | 99.33% |
| Box 13 statutory employee | `box_13.statutory_employee` | 150 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 150 | 0 | 100.00% |
| Employee last name | `employee.last_name` | 150 | 0 | 100.00% |
| Employee SSN | `employee.ssn` | 150 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 150 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 150 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 150 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 150 | 0 | 100.00% |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 150 | 0 | 100.00% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 150 | 0 | 100.00% |
| Box 4 Social Security tax withheld | `federal_wages_and_taxes.box_4_social_security_tax_withheld` | 150 | 0 | 100.00% |
| Box 7 Social Security tips | `federal_wages_and_taxes.box_7_social_security_tips` | 150 | 0 | 100.00% |
| Box 8 allocated tips | `federal_wages_and_taxes.box_8_allocated_tips` | 150 | 0 | 100.00% |
| Document type | `metadata.document_type` | 150 | 0 | 100.00% |
| Schema version | `metadata.schema_version` | 150 | 0 | 100.00% |
| Tax year | `metadata.tax_year` | 150 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Employee first name (`employee.first_name`) | 10 |
| Employee middle initial (`employee.middle_initial`) | 9 |
| Box 13 retirement plan (`box_13.retirement_plan`) | 5 |
| Employer EIN (`employer.ein`) | 2 |
| Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 2 |
| Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1 |
| Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1 |

Showing all 30 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900021-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 78-9941160 | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Jesús | Jesus | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Alexis | Alexis Ss | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | S | `null` | ocr |
| symage_900037-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Julie | dalle | ocr |
| symage_900046-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900046-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | John | John WwW | ocr |
| symage_900046-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | W | `null` | ocr |
| symage_900050-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900052-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Óliver | Oliver | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Alicia | Alicia ici | ocr |
| symage_900060-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900063-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 3.08E+4 | `null` | ocr |
| symage_900063-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 446.6 | `null` | ocr |
| symage_900065-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900075-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 8.15E+4 | 81 | ocr |
| symage_900083-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | C | `null` | ocr |
| symage_900088-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Ethan | Ethan WwW | ocr |
| symage_900088-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | W | `null` | ocr |
| symage_900102-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | C | `null` | ocr |
| symage_900103-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Adán | Adan WwW | ocr |
| symage_900103-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | W | `null` | ocr |
| symage_900119-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Jeffrey | veffrey | ocr |
| symage_900119-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | A | `null` | ocr |
| symage_900119-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 73-3368011 | `null` | ocr |
| symage_900123-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900123-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1294.85 | 1204.85 | ocr |
| symage_900135-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | I | `null` | ocr |
| symage_900143-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | William | William Wi | ocr |
| symage_900147-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | C | `null` | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Employee first name was the lowest-accuracy field at 93.33%.
These results do not establish production readiness by themselves.
