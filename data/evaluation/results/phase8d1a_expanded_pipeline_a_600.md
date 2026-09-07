# Phase8D1A Expanded Pipeline A 600

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
| Fields checked | 25,920 |
| Correct fields | 25,829 |
| Field accuracy | 99.65% |
| Average processing time per document | 1.350 seconds |

## Accuracy by Variant

| Document condition | Documents | Field accuracy |
| --- | ---: | ---: |
| Blurred | 150 | 99.98% |
| JPEG compressed | 150 | 99.98% |
| Clean render | 150 | 100.00% |
| Rotated | 150 | 98.63% |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Employer Address Address Line 1 | `employer.address.address_line_1` | 589 | 11 | 98.17% |
| Employer Address City | `employer.address.city` | 591 | 9 | 98.50% |
| Employer Address Country | `employer.address.country` | 591 | 9 | 98.50% |
| Employer Address Postal Code | `employer.address.postal_code` | 591 | 9 | 98.50% |
| Employer Address State | `employer.address.state` | 591 | 9 | 98.50% |
| Employee Address Address Line 1 | `employee.address.address_line_1` | 592 | 8 | 98.67% |
| Employee Address City | `employee.address.city` | 592 | 8 | 98.67% |
| Employee Address Country | `employee.address.country` | 592 | 8 | 98.67% |
| Employee Address Postal Code | `employee.address.postal_code` | 592 | 8 | 98.67% |
| Employee Address State | `employee.address.state` | 592 | 8 | 98.67% |
| Employer name | `employer.name` | 596 | 4 | 99.33% |
| Box 12 Entries 0 Amount | `box_12_entries[0].amount` | 468 | 0 | 100.00% |
| Box 12 Entries 0 Code | `box_12_entries[0].code` | 468 | 0 | 100.00% |
| Box 12 Entries 1 Amount | `box_12_entries[1].amount` | 192 | 0 | 100.00% |
| Box 12 Entries 1 Code | `box_12_entries[1].code` | 192 | 0 | 100.00% |
| Box 13 retirement plan | `box_13.retirement_plan` | 600 | 0 | 100.00% |
| Box 13 statutory employee | `box_13.statutory_employee` | 600 | 0 | 100.00% |
| Box 13 third-party sick pay | `box_13.third_party_sick_pay` | 600 | 0 | 100.00% |
| Employee first name | `employee.first_name` | 600 | 0 | 100.00% |
| Employee last name | `employee.last_name` | 600 | 0 | 100.00% |
| Employee middle initial | `employee.middle_initial` | 600 | 0 | 100.00% |
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
| State Local Entries 0 Box 15 Employer State Id Number | `state_local_entries[0].box_15_employer_state_id_number` | 600 | 0 | 100.00% |
| State Local Entries 0 Box 15 State | `state_local_entries[0].box_15_state` | 600 | 0 | 100.00% |
| State Local Entries 0 Box 16 State Wages Tips Etc | `state_local_entries[0].box_16_state_wages_tips_etc` | 600 | 0 | 100.00% |
| State Local Entries 0 Box 17 State Income Tax | `state_local_entries[0].box_17_state_income_tax` | 600 | 0 | 100.00% |
| State Local Entries 0 Box 18 Local Wages Tips Etc | `state_local_entries[0].box_18_local_wages_tips_etc` | 600 | 0 | 100.00% |
| State Local Entries 0 Box 19 Local Income Tax | `state_local_entries[0].box_19_local_income_tax` | 600 | 0 | 100.00% |
| State Local Entries 0 Box 20 Locality Name | `state_local_entries[0].box_20_locality_name` | 600 | 0 | 100.00% |

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Employer Address Address Line 1 (`employer.address.address_line_1`) | 11 |
| Employer Address City (`employer.address.city`) | 9 |
| Employer Address Country (`employer.address.country`) | 9 |
| Employer Address Postal Code (`employer.address.postal_code`) | 9 |
| Employer Address State (`employer.address.state`) | 9 |
| Employee Address Address Line 1 (`employee.address.address_line_1`) | 8 |
| Employee Address City (`employee.address.city`) | 8 |
| Employee Address Country (`employee.address.country`) | 8 |
| Employee Address Postal Code (`employee.address.postal_code`) | 8 |
| Employee Address State (`employee.address.state`) | 8 |
| Employer name (`employer.name`) | 4 |

Showing all 91 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900027-irs_w2_single_page_2026-p0 | Blurred | Employer Address Address Line 1 (`employer.address.address_line_1`) | 369 Pennsylvania Ave N | 369 Pennsylvania Áve N | ocr |
| symage_900061-irs_w2_single_page_2026-p0 | JPEG compressed | Employer Address Address Line 1 (`employer.address.address_line_1`) | 9992 S Jefferson St | 9992 Š Jefferson St | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 34 Spring Creek Rd | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | Colorado Springs | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 80919 | `null` | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | CO | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 9099 Zerex St | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | Colorado Springs | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 80949 | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | CO | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 288 E-470 | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | Grand Junction | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 81501 | `null` | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | CO | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 8 Whitesburg Rd | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | Cumberland City | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 37050 | `null` | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | TN | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 2861 Geneva Ponce De Leon Rd | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | Bartow | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 33830 | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | FL | `null` | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Elan Consulting Corp | Elan Consulting Corp 2861 Geneva Ponce De Leon Rd | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 260 Grant St | `null` | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | East Vandergrift | `null` | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 15629 | `null` | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | PA | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 363 N Main St | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | Cumberland Furnace | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 37051 | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | TN | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 6878 Normandy Tullahoma Rd | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | Memphis | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 38132 | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | TN | `null` | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Bespoke Designs LLC | Bespoke Designs LLC 6878 Normandy Tullahoma Rd | ocr |
| symage_900049-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 736 Blenheim Hwy | `null` | ocr |
| symage_900049-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | North Charleston | `null` | ocr |
| symage_900049-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900049-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 29415 | `null` | ocr |
| symage_900049-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | SC | `null` | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 660 S Loop 289 | `null` | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | Corpus Christi | `null` | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 78416 | `null` | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | TX | `null` | ocr |
| symage_900077-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 7551 Airport Expy | `null` | ocr |
| symage_900077-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | West Springfield | `null` | ocr |
| symage_900077-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900077-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 16443 | `null` | ocr |
| symage_900077-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | PA | `null` | ocr |
| symage_900081-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 4 S Meridian St | `null` | ocr |
| symage_900081-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | Thompsons Station | `null` | ocr |
| symage_900081-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900081-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 37179 | `null` | ocr |
| symage_900081-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | TN | `null` | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 875 Francis Case Memorial Brg | `null` | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | Washington | `null` | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 20203 | `null` | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | DC | `null` | ocr |
| symage_900082-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | FutureReady Services | FutureReady Services 875 Francis Case Memorial Brg | ocr |
| symage_900087-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 840 Slide Rd | `null` | ocr |
| symage_900087-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | South Padre Island | `null` | ocr |
| symage_900087-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900087-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 78597 | `null` | ocr |
| symage_900087-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | TX | `null` | ocr |
| symage_900125-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 6468 Lake Front Dr | `null` | ocr |
| symage_900125-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | Chenango Bridge | `null` | ocr |
| symage_900125-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900125-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 13745 | `null` | ocr |
| symage_900125-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | NY | `null` | ocr |
| symage_900137-irs_w2_single_page_2026-p0 | Rotated | Employee Address Address Line 1 (`employee.address.address_line_1`) | 3086 Marina Fwy | `null` | ocr |
| symage_900137-irs_w2_single_page_2026-p0 | Rotated | Employee Address City (`employee.address.city`) | Huntington Park | `null` | ocr |
| symage_900137-irs_w2_single_page_2026-p0 | Rotated | Employee Address Country (`employee.address.country`) | US | `null` | ocr |
| symage_900137-irs_w2_single_page_2026-p0 | Rotated | Employee Address Postal Code (`employee.address.postal_code`) | 90255 | `null` | ocr |
| symage_900137-irs_w2_single_page_2026-p0 | Rotated | Employee Address State (`employee.address.state`) | CA | `null` | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Employer Address Address Line 1 (`employer.address.address_line_1`) | 4522 Eastern Transportation Corridor | `null` | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Employer Address City (`employer.address.city`) | Cathedral City | `null` | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Employer Address Country (`employer.address.country`) | US | `null` | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Employer Address Postal Code (`employer.address.postal_code`) | 92234 | `null` | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Employer Address State (`employer.address.state`) | CA | `null` | ocr |
| symage_900146-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Global Insights Corp | Global Insights Corp 4522 Eastern Transportation Corridor | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Rotated documents had the lowest field accuracy at 98.63%.
Employer Address Address Line 1 was the lowest-accuracy field at 98.17%.
These results do not establish production readiness by themselves.
