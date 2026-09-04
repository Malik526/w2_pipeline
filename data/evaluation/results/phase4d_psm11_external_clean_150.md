# Phase4D Psm11 External Clean 150

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
| Correct fields | 3,141 |
| Field accuracy | 91.04% |
| Average processing time per document | 2.154 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 0 | 150 | 0.00% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 0 | 150 | 0.00% |
| Employee SSN | `employee.ssn` | 145 | 5 | 96.67% |
| Employee first name | `employee.first_name` | 147 | 3 | 98.00% |
| Employee middle initial | `employee.middle_initial` | 149 | 1 | 99.33% |
| Box 13 retirement plan | `box_13.retirement_plan` | 150 | 0 | 100.00% |
| Box 13 statutory employee | `box_13.statutory_employee` | 150 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 150 | 0 | 100.00% |
| Employee last name | `employee.last_name` | 150 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 150 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 150 | 0 | 100.00% |
| Employer EIN | `employer.ein` | 150 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 150 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 150 | 0 | 100.00% |
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
| Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 150 |
| Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 150 |
| Employee SSN (`employee.ssn`) | 5 |
| Employee first name (`employee.first_name`) | 3 |
| Employee middle initial (`employee.middle_initial`) | 1 |

Showing 100 of 309 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 1.032E+5 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 14996.38 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 114858 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 21930.26 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 85911 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 8327.12 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 1.44E+4 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 148.86 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 4.94E+4 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 4736.23 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 83419 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 6391.76 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 6.91E+4 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 8272.28 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 86734 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 9705.85 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 137467 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 40324.92 | `null` | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 8.4E+3 | `null` | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 100.5 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 23622 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 293.91 | `null` | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 5.73E+4 | `null` | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 4925.58 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 9729 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 157.96 | `null` | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 1.696E+5 | `null` | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 28593.62 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 3964 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 41.15 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 1.94E+4 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 649.5 | `null` | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 8.02E+4 | `null` | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 11689.99 | `null` | ocr |
| symage_900017-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 8147 | `null` | ocr |
| symage_900017-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 131.56 | `null` | ocr |
| symage_900018-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 10071 | `null` | ocr |
| symage_900018-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 150.31 | `null` | ocr |
| symage_900019-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 29095 | `null` | ocr |
| symage_900019-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 194.01 | `null` | ocr |
| symage_900020-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 23214 | `null` | ocr |
| symage_900020-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 1302 | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 28885 | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 2531.81 | `null` | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 4.18E+4 | `null` | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 1654.22 | `null` | ocr |
| symage_900023-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 57973 | `null` | ocr |
| symage_900023-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 7239.09 | `null` | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 7.93E+4 | `null` | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 8118.92 | `null` | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 3.08E+4 | `null` | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 2239.4 | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Jesús | Jesus | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 286167 | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 71375.67 | `null` | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 14397 | `null` | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 174.93 | `null` | ocr |
| symage_900028-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 41177 | `null` | ocr |
| symage_900028-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 3436.05 | `null` | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 8.4E+3 | `null` | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 103.25 | `null` | ocr |
| symage_900030-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 35424 | `null` | ocr |
| symage_900030-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 1573.02 | `null` | ocr |
| symage_900031-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 51149 | `null` | ocr |
| symage_900031-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 4675.6 | `null` | ocr |
| symage_900032-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 12861 | `null` | ocr |
| symage_900032-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 173.33 | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 6.83E+4 | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 6062.27 | `null` | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 3.4E+4 | `null` | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 2993.38 | `null` | ocr |
| symage_900035-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 531-59-0815 | `null` | ocr |
| symage_900035-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 4.851E+4 | `null` | ocr |
| symage_900035-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 2520.68 | `null` | ocr |
| symage_900036-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 10026 | `null` | ocr |
| symage_900036-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 125.72 | `null` | ocr |
| symage_900037-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 31011 | `null` | ocr |
| symage_900037-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 2597.44 | `null` | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 5.09E+4 | `null` | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 2324.42 | `null` | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 5.9E+4 | `null` | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 3672.86 | `null` | ocr |
| symage_900040-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 24038 | `null` | ocr |
| symage_900040-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 293.33 | `null` | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 5.39E+4 | `null` | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 3666.95 | `null` | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 7.3E+3 | `null` | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 101 | `null` | ocr |
| symage_900043-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 21481 | `null` | ocr |
| symage_900043-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 761.52 | `null` | ocr |
| symage_900044-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 51486 | `null` | ocr |
| symage_900044-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 7002.13 | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 53806 | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 5580.72 | `null` | ocr |
| symage_900046-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 21942 | `null` | ocr |
| symage_900046-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 1046.35 | `null` | ocr |
| symage_900047-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 3.358E+4 | `null` | ocr |
| symage_900047-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 1377.58 | `null` | ocr |
| symage_900048-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 16849 | `null` | ocr |
| symage_900048-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 358.77 | `null` | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Box 1 wages, tips, other compensation was the lowest-accuracy field at 0.00%.
These results do not establish production readiness by themselves.
