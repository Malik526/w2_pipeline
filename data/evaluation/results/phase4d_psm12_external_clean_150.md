# Phase4D Psm12 External Clean 150

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
| Correct fields | 1,742 |
| Field accuracy | 50.49% |
| Average processing time per document | 2.348 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Employee first name | `employee.first_name` | 0 | 150 | 0.00% |
| Employee last name | `employee.last_name` | 0 | 150 | 0.00% |
| Employee SSN | `employee.ssn` | 0 | 150 | 0.00% |
| Employer EIN | `employer.ein` | 0 | 150 | 0.00% |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 0 | 150 | 0.00% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 0 | 150 | 0.00% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 0 | 150 | 0.00% |
| Box 4 Social Security tax withheld | `federal_wages_and_taxes.box_4_social_security_tax_withheld` | 0 | 150 | 0.00% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 0 | 150 | 0.00% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 0 | 150 | 0.00% |
| Employee middle initial | `employee.middle_initial` | 32 | 118 | 21.33% |
| Box 13 retirement plan | `box_13.retirement_plan` | 60 | 90 | 40.00% |
| Box 13 statutory employee | `box_13.statutory_employee` | 150 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 150 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 150 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 150 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 150 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 150 | 0 | 100.00% |
| Box 7 Social Security tips | `federal_wages_and_taxes.box_7_social_security_tips` | 150 | 0 | 100.00% |
| Box 8 allocated tips | `federal_wages_and_taxes.box_8_allocated_tips` | 150 | 0 | 100.00% |
| Document type | `metadata.document_type` | 150 | 0 | 100.00% |
| Schema version | `metadata.schema_version` | 150 | 0 | 100.00% |
| Tax year | `metadata.tax_year` | 150 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Employee first name (`employee.first_name`) | 150 |
| Employee last name (`employee.last_name`) | 150 |
| Employee SSN (`employee.ssn`) | 150 |
| Employer EIN (`employer.ein`) | 150 |
| Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 150 |
| Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 150 |
| Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 150 |
| Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 150 |
| Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 150 |
| Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 150 |
| Employee middle initial (`employee.middle_initial`) | 118 |
| Box 13 retirement plan (`box_13.retirement_plan`) | 90 |

Showing 100 of 1,708 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Lori | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Smith | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 524-29-7818 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 42-1723377 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 1.032E+5 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 14996.38 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.032E+5 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 6398.4 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.032E+5 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1496.4 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Steven | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Armstrong | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 242-48-4959 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 75-5696876 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 114858 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 21930.26 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.22E+5 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 7564 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.22E+5 | `null` | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1769 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Violeta | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Prince | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | L | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 080-52-0080 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 51-6163111 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 85911 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 8327.12 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 9.4E+4 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 5828 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 9.4E+4 | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1363 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Isabel | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Lopez | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | K | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 568-92-4459 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 63-4467342 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 1.44E+4 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 148.86 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.44E+4 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 892.8 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.44E+4 | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 208.8 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Jonathan | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Mosley | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | W | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 050-15-9561 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 62-6885566 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 4.94E+4 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 4736.23 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 4.94E+4 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 3062.8 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 4.94E+4 | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 716.3 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | David | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Rodriguez | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | G | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 386-13-1874 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 23-8093067 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 83419 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 6391.76 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 8.76E+4 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 5431.2 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 8.76E+4 | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1270.2 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Melissa | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Olson | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 567-13-3157 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 74-9289871 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 6.91E+4 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 8272.28 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 6.91E+4 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 4284.2 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 6.91E+4 | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1001.95 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | Daniel | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Cooper | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | J | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 151-36-6768 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 30-7291978 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 86734 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 9705.85 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 9.7E+4 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 6014 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 9.7E+4 | `null` | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Clean render | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1406.5 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 13 retirement plan (`box_13.retirement_plan`) | True | False | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Employee first name (`employee.first_name`) | William | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Employee last name (`employee.last_name`) | Lawson | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Employee middle initial (`employee.middle_initial`) | R | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Employee SSN (`employee.ssn`) | 608-88-7333 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Employer EIN (`employer.ein`) | 90-9914816 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 1 wages, tips, other compensation (`federal_wages_and_taxes.box_1_wages_tips_other_compensation`) | 137467 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 2 federal income tax withheld (`federal_wages_and_taxes.box_2_federal_income_tax_withheld`) | 40324.92 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.584E+5 | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Clean render | Box 4 Social Security tax withheld (`federal_wages_and_taxes.box_4_social_security_tax_withheld`) | 9820.8 | `null` | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Employee first name was the lowest-accuracy field at 0.00%.
These results do not establish production readiness by themselves.
