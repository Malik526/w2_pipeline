# Phase4E Paddleocr Gpu Checkbox Vision External All Variants 600

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
| Correct fields | 13,472 |
| Field accuracy | 97.62% |
| Average processing time per document | 1.330 seconds |

## Accuracy by Variant

| Document condition | Documents | Field accuracy |
| --- | ---: | ---: |
| Blurred | 150 | 100.00% |
| JPEG compressed | 150 | 100.00% |
| Clean render | 150 | 100.00% |
| Rotated | 150 | 90.49% |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Employee first name | `employee.first_name` | 450 | 150 | 75.00% |
| Employee middle initial | `employee.middle_initial` | 482 | 118 | 80.33% |
| Box 13 retirement plan | `box_13.retirement_plan` | 540 | 60 | 90.00% |
| Box 13 statutory employee | `box_13.statutory_employee` | 600 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 600 | 0 | 100.00% |
| Employee last name | `employee.last_name` | 600 | 0 | 100.00% |
| Employee SSN | `employee.ssn` | 600 | 0 | 100.00% |
| Employee suffix | `employee.suffix` | 600 | 0 | 100.00% |
| Employer control number | `employer.control_number` | 600 | 0 | 100.00% |
| Employer EIN | `employer.ein` | 600 | 0 | 100.00% |
| Box 10 dependent care benefits | `federal_wages_and_taxes.box_10_dependent_care_benefits` | 600 | 0 | 100.00% |
| Box 11 nonqualified plans | `federal_wages_and_taxes.box_11_nonqualified_plans` | 600 | 0 | 100.00% |
| Box 1 wages, tips, other compensation | `federal_wages_and_taxes.box_1_wages_tips_other_compensation` | 600 | 0 | 100.00% |
| Box 2 federal income tax withheld | `federal_wages_and_taxes.box_2_federal_income_tax_withheld` | 600 | 0 | 100.00% |
| Box 3 Social Security wages | `federal_wages_and_taxes.box_3_social_security_wages` | 600 | 0 | 100.00% |
| Box 4 Social Security tax withheld | `federal_wages_and_taxes.box_4_social_security_tax_withheld` | 600 | 0 | 100.00% |
| Box 5 Medicare wages and tips | `federal_wages_and_taxes.box_5_medicare_wages_and_tips` | 600 | 0 | 100.00% |
| Box 6 Medicare tax withheld | `federal_wages_and_taxes.box_6_medicare_tax_withheld` | 600 | 0 | 100.00% |
| Box 7 Social Security tips | `federal_wages_and_taxes.box_7_social_security_tips` | 600 | 0 | 100.00% |
| Box 8 allocated tips | `federal_wages_and_taxes.box_8_allocated_tips` | 600 | 0 | 100.00% |
| Document type | `metadata.document_type` | 600 | 0 | 100.00% |
| Schema version | `metadata.schema_version` | 600 | 0 | 100.00% |
| Tax year | `metadata.tax_year` | 600 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Employee first name (`employee.first_name`) | 150 |
| Employee middle initial (`employee.middle_initial`) | 118 |
| Box 13 retirement plan (`box_13.retirement_plan`) | 60 |

Showing 100 of 328 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Lori | Lori e Employee's first name and initial | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Steven | Steven D e Employee's first name and initial | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Violeta | Violeta L e Employee's first name and initial | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | L | `null` | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Isabel | Isabel K e Employee's first name and initial | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | K | `null` | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Jonathan | Jonathan W e Employee's first name and initial | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | W | `null` | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | David | David G e Employee's first name and initial | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | G | `null` | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Melissa | Melissa e Employee's first name and initial | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Daniel | Daniel J e Employee's first name and initial | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | J | `null` | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | William | William R e Employee's first name and initial | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | R | `null` | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Marisa | Marisa e Employee's first name and initial | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Carol | Carol K e Employee's first name and initial | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | K | `null` | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Scott | Scott D e Employee's first name and initial | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Rebecca | Rebecca J e Employee's first name and initial | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | J | `null` | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Jeffrey | Jeffrey B e Employee's first name and initial | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | B | `null` | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Virginia | Virginia F e Employee's first name and initial | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | F | `null` | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Elsa | Elsa e Employee's first name and initial | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Samantha | Samantha N e Employee's first name and initial | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | N | `null` | ocr |
| symage_900017-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | James | James B e Employee's first name and initial | ocr |
| symage_900017-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | B | `null` | ocr |
| symage_900018-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Brandon | Brandon e Employee's first name and initial | ocr |
| symage_900019-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Yvette | Yvette K e Employee's first name and initial | ocr |
| symage_900019-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | K | `null` | ocr |
| symage_900020-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Rita | Rita e Employee's first name and initial | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Lauren | Lauren M e Employee's first name and initial | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | M | `null` | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Christopher | Christopher S e Employee's first name and initial | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | S | `null` | ocr |
| symage_900023-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | James | James E e Employee's first name and initial | ocr |
| symage_900023-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | E | `null` | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Nicole | Nicole H e Employee's first name and initial | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | H | `null` | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Daniel | Daniel e Employee's first name and initial | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Jesús | Jesús D e Employee's first name and initial | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Alexis | Alexis S e Employee's first name and initial | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | S | `null` | ocr |
| symage_900028-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Felix | Felix E e Employee's first name and initial | ocr |
| symage_900028-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | E | `null` | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Anthony | Anthony R e Employee's first name and initial | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | R | `null` | ocr |
| symage_900030-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Melissa | Melissa F e Employee's first name and initial | ocr |
| symage_900030-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | F | `null` | ocr |
| symage_900031-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Calvin | Calvin D e Employee's first name and initial | ocr |
| symage_900031-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900032-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Crystal | Crystal L e Employee's first name and initial | ocr |
| symage_900032-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | L | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Thomas | Thomas e Employee's first name and initial | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Nicholas | Nicholas D e Employee's first name and initial | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900035-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | David | David M e Employee's first name and initial | ocr |
| symage_900035-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | M | `null` | ocr |
| symage_900036-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Amanda | Amanda L e Employee's first name and initial | ocr |
| symage_900036-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | L | `null` | ocr |
| symage_900037-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Julie | Julie D e Employee's first name and initial | ocr |
| symage_900037-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | D | `null` | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Spencer | Spencer W e Employee's first name and initial | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | W | `null` | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Jonathan | Jonathan H e Employee's first name and initial | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | H | `null` | ocr |
| symage_900040-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Tammy | Tammy e Employee's first name and initial | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Dawn | Dawn M e Employee's first name and initial | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | M | `null` | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Aaron | Aaron e Employee's first name and initial | ocr |
| symage_900043-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Lauren | Lauren J e Employee's first name and initial | ocr |
| symage_900043-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | J | `null` | ocr |
| symage_900044-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Mark | Mark J e Employee's first name and initial | ocr |
| symage_900044-irs_w2_single_page_2026-p0 | Rotated | Employee middle initial (`employee.middle_initial`) | J | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employee first name (`employee.first_name`) | Joshua | Joshua e Employee's first name and initial | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Rotated documents had the lowest field accuracy at 90.49%.
Employee first name was the lowest-accuracy field at 75.00%.
These results do not establish production readiness by themselves.
