# Phase4E Paddleocr Gpu External Clean 150

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
| Correct fields | 3,360 |
| Field accuracy | 97.39% |
| Average processing time per document | 1.349 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Box 13 retirement plan | `box_13.retirement_plan` | 60 | 90 | 40.00% |
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
| Box 13 retirement plan (`box_13.retirement_plan`) | 90 |

Showing all 90 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900017-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900018-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900019-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900020-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900023-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900028-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900030-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900031-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900032-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900035-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900036-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900037-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900040-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900043-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900044-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900046-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900047-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900048-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900049-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900050-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900051-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900053-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900054-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900056-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900057-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900059-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900060-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900062-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900064-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900065-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900066-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900067-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900068-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900071-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900072-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900077-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900078-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900084-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900086-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900087-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900089-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900090-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900092-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900093-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900097-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900100-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900101-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900102-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900104-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900105-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900106-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900107-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900110-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900111-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900112-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900114-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900116-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900119-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900121-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900122-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900123-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900124-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900125-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900126-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900128-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900132-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900134-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900135-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900136-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900137-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900139-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900140-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900141-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900144-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900147-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900148-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900149-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Box 13 retirement plan was the lowest-accuracy field at 40.00%.
These results do not establish production readiness by themselves.
