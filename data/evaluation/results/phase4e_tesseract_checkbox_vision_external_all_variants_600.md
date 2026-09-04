# Phase4E Tesseract Checkbox Vision External All Variants 600

Field accuracy is the percentage of individual W-2 values that matched the known correct answer.
A document failure means the pipeline could not complete extraction for the document at all.
Failure inspection values are intended for synthetic evaluation data; future real-data reports should redact sensitive values.

## Summary

| Metric | Value |
| --- | ---: |
| Pipeline | pipeline_a |
| Dataset/source | Symage/synthetic-us-forms-preview |
| Document condition / variant scope | Blurred, JPEG compressed, Clean render, Rotated |
| Documents tested | 600 |
| Successful documents | 600 |
| Failed documents | 0 |
| Failure rate | 0.00% |
| Fields checked | 13,800 |
| Correct fields | 12,279 |
| Field accuracy | 88.98% |
| Average processing time per document | 2.319 seconds |

## Accuracy by Variant

| Document condition | Documents | Field accuracy |
| --- | ---: | ---: |
| Blurred | 150 | 67.71% |
| JPEG compressed | 150 | 98.96% |
| Clean render | 150 | 99.28% |
| Rotated | 150 | 89.97% |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Employee first name | `employee.first_name` | 322 | 278 | 53.67% |
| Employee middle initial | `employee.middle_initial` | 382 | 218 | 63.67% |
| Box 13 retirement plan | `box_13.retirement_plan` | 472 | 128 | 78.67% |
| Employee last name | `employee.last_name` | 495 | 105 | 82.50% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 495 | 105 | 82.50% |
| Employee SSN | `employee.ssn` | 498 | 102 | 83.00% |
| Employer EIN | `employer.ein` | 498 | 102 | 83.00% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 501 | 99 | 83.50% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 501 | 99 | 83.50% |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 505 | 95 | 84.17% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 505 | 95 | 84.17% |
| Box 4 Social Security tax withheld | `federal_wages_and_taxes.box_4_social_security_tax_withheld` | 505 | 95 | 84.17% |
| Box 13 statutory employee | `box_13.statutory_employee` | 600 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 600 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 600 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 600 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 600 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 600 | 0 | 100.00% |
| Box 7 Social Security tips | `federal_wages_and_taxes.box_7_social_security_tips` | 600 | 0 | 100.00% |
| Box 8 allocated tips | `federal_wages_and_taxes.box_8_allocated_tips` | 600 | 0 | 100.00% |
| Document type | `metadata.document_type` | 600 | 0 | 100.00% |
| Schema version | `metadata.schema_version` | 600 | 0 | 100.00% |
| Tax year | `metadata.tax_year` | 600 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Employee first name (`employee.first_name`) | 278 |
| Employee middle initial (`employee.middle_initial`) | 218 |
| Box 13 retirement plan (`box_13.retirement_plan`) | 128 |
| Employee last name (`employee.last_name`) | 105 |
| Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 105 |
| Employee SSN (`employee.ssn`) | 102 |
| Employer EIN (`employer.ein`) | 102 |
| Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 99 |
| Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 99 |
| Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 95 |
| Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 95 |
| Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 95 |

Showing 100 of 1,521 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900000-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Smith | Sm ith | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Steven | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Armstrong | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 242-48-4959 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 75-5696876 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 114858 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 21930.26 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.22E+5 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 7564 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.22E+5 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1769 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Violeta | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Prince | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | L | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 080-52-0080 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 51-6163111 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 85911 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 8327.12 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 9.4E+4 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 5828 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 9.4E+4 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1363 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Daniel | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Cooper | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | J | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 151-36-6768 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 30-7291978 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 86734 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 9705.85 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 9.7E+4 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 6014 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 9.7E+4 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1406.5 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | William | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Lawson | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | R | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 608-88-7333 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 90-9914816 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 137467 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 40324.92 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.584E+5 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 9820.8 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.584E+5 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 2296.8 | `null` | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Marisa | M ari sa | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Carol | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Jordan | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | K | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 302-40-3006 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 76-3256636 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 23622 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 293.91 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 2.59E+4 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 1605.8 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 2.59E+4 | `null` | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 375.55 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Rebecca | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Reynolds | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | J | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 601-42-7683 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 34-7954828 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 9729 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 157.96 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.1E+4 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 682 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.1E+4 | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 159.5 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Virginia | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Lee | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | F | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 607-02-7127 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 55-1908841 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 3964 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 41.15 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 4.5E+3 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 279 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 4.5E+3 | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 65.25 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Elsa | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Sloan | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 278-15-5044 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Employer EIN (`employer.ein`) | 29-9350958 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 1.94E+4 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 649.5 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.94E+4 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 1202.8 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.94E+4 | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Blurred | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 281.3 | `null` | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Blurred | Employee first name (`employee.first_name`) | Samantha | `null` | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Blurred | Employee last name (`employee.last_name`) | Willis | `null` | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Blurred | Employee middle initial (`employee.middle_initial`) | N | `null` | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Blurred | Employee SSN (`employee.ssn`) | 612-44-0278 | `null` | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Blurred documents had the lowest field accuracy at 67.71%.
Employee first name was the lowest-accuracy field at 53.67%.
These results do not establish production readiness by themselves.
