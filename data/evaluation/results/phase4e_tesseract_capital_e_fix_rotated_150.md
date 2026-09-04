# Phase4E Tesseract Capital E Fix Rotated 150

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
| Fields checked | 3,450 |
| Correct fields | 3,365 |
| Field accuracy | 97.54% |
| Average processing time per document | 2.361 seconds |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Box 13 retirement plan | `box_13.retirement_plan` | 90 | 60 | 60.00% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 142 | 8 | 94.67% |
| Employee first name | `employee.first_name` | 146 | 4 | 97.33% |
| Employee SSN | `employee.ssn` | 146 | 4 | 97.33% |
| Employee middle initial | `employee.middle_initial` | 147 | 3 | 98.00% |
| Employer EIN | `employer.ein` | 148 | 2 | 98.67% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 148 | 2 | 98.67% |
| Employee last name | `employee.last_name` | 149 | 1 | 99.33% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 149 | 1 | 99.33% |
| Box 13 statutory employee | `box_13.statutory_employee` | 150 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 150 | 0 | 100.00% |
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
| Box 13 retirement plan (`box_13.retirement_plan`) | 60 |
| Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 8 |
| Employee first name (`employee.first_name`) | 4 |
| Employee SSN (`employee.ssn`) | 4 |
| Employee middle initial (`employee.middle_initial`) | 3 |
| Employer EIN (`employer.ein`) | 2 |
| Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 2 |
| Employee last name (`employee.last_name`) | 1 |
| Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 1 |

Showing all 85 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.1E+4 | 11 | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Rotated | Employer EIN (`employer.ein`) | 19-2042752 | 49-2042752 | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Jesús | Jesus | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.64E+4 | 6.4E+3 | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900031-irs_w2_single_page_2026-p0 | Rotated | Employee SSN (`employee.ssn`) | 420-81-4364 | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900051-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 2.11E+4 | 1E+2 | ocr |
| symage_900052-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900052-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Óliver | Oliver | ocr |
| symage_900055-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900061-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900062-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | C | `null` | ocr |
| symage_900063-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900068-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | C | `null` | ocr |
| symage_900068-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 8.1E+3 | 0 | ocr |
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
| symage_900083-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900085-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900086-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 5.13E+4 | 3E+2 | ocr |
| symage_900088-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900088-irs_w2_single_page_2026-p0 | Rotated | Employer EIN (`employer.ein`) | 95-9834011 | `null` | ocr |
| symage_900091-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900093-irs_w2_single_page_2026-p0 | Rotated | Employee SSN (`employee.ssn`) | 258-51-0064 | `null` | ocr |
| symage_900093-irs_w2_single_page_2026-p0 | Rotated | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 1.47E+4 | `null` | ocr |
| symage_900093-irs_w2_single_page_2026-p0 | Rotated | Box 6 Medicare tax withheld (`federal_wages_and_taxes.box_6_medicare_tax_withheld`) | 213.15 | `null` | ocr |
| symage_900094-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900095-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900096-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900097-irs_w2_single_page_2026-p0 | Rotated | Employee SSN (`employee.ssn`) | 126-44-7007 | `null` | ocr |
| symage_900098-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900099-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900100-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 8.14E+4 | 4E+2 | ocr |
| symage_900103-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900103-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Adán | Adan | ocr |
| symage_900108-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900109-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900113-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900115-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900117-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900118-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900118-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Logan | `null` | ocr |
| symage_900120-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900126-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 3.19E+4 | 9E+2 | ocr |
| symage_900127-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900127-irs_w2_single_page_2026-p0 | Rotated | Box 3 Social Security wages (`federal_wages_and_taxes.box_3_social_security_wages`) | 1.845E+5 | 8.45E+4 | ocr |
| symage_900129-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900130-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900131-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900132-irs_w2_single_page_2026-p0 | Rotated | Employee last name (`employee.last_name`) | Turner | `null` | ocr |
| symage_900133-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900135-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | I | `null` | ocr |
| symage_900138-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900140-irs_w2_single_page_2026-p0 | Rotated | Employee SSN (`employee.ssn`) | 642-21-3542 | `null` | ocr |
| symage_900142-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900143-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900145-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Box 5 Medicare wages and tips (`federal_wages_and_taxes.box_5_medicare_wages_and_tips`) | 4.13E+4 | 4.43E+4 | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Box 13 retirement plan was the lowest-accuracy field at 60.00%.
These results do not establish production readiness by themselves.
