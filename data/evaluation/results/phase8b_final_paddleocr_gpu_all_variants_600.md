# Phase8B Final Paddleocr Gpu All Variants 600

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
| Fields checked | 14,400 |
| Correct fields | 14,190 |
| Field accuracy | 98.54% |
| Average processing time per document | 1.301 seconds |

## Accuracy by Variant

| Document condition | Documents | Field accuracy |
| --- | ---: | ---: |
| Blurred | 150 | 100.00% |
| JPEG compressed | 150 | 100.00% |
| Clean render | 150 | 100.00% |
| Rotated | 150 | 94.17% |

## Accuracy by Field

| Field | Canonical path | Correct | Incorrect | Accuracy |
| --- | --- | ---: | ---: | ---: |
| Employer name | `employer.name` | 450 | 150 | 75.00% |
| Box 13 retirement plan | `box_13.retirement_plan` | 540 | 60 | 90.00% |
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

## Failure Inspection

| Field | Incorrect results |
| --- | ---: |
| Employer name (`employer.name`) | 150 |
| Box 13 retirement plan (`box_13.retirement_plan`) | 60 |

Showing 100 of 210 incorrect field results.

| Document | Variant | Field | Expected | Predicted | Route |
| --- | --- | --- | --- | --- | --- |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900000-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Advantage Recruiting LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900001-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Timberline Trading Co. | c Employer's name, address, and ZIP code | ocr |
| symage_900002-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | BlueWave Enterprises | c Employer's name, address, and ZIP code | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900003-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Infinity Enterprises Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900004-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Bright Horizons Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900005-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Catalyst Energy Solutions | c Employer's name, address, and ZIP code | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900006-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Evergreen Solutions LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900007-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Tidal Wave Enterprises | c Employer's name, address, and ZIP code | ocr |
| symage_900008-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Streamline Operations Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900009-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | ClearWater Financial Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900010-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | WorldWise Strategies Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900011-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Ascend Financial Group Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900012-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Crescent Moon Designs LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900013-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Verde Energy Solutions LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900014-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Evergreen Technologies Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900015-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Beacon Point Technologies | c Employer's name, address, and ZIP code | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900016-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Digital Frontier Solutions | c Employer's name, address, and ZIP code | ocr |
| symage_900017-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Vanguard Systems | c Employer's name, address, and ZIP code | ocr |
| symage_900018-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Synergy Business Solutions | c Employer's name, address, and ZIP code | ocr |
| symage_900019-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Pioneer Technologies Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900020-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Fortress Security LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900021-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Maple Leaf Industries | c Employer's name, address, and ZIP code | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900022-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Elemental Designs Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900023-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Whirlwind Logistics LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900024-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Neon Path Consulting | c Employer's name, address, and ZIP code | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900025-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | FutureTech Developments | c Employer's name, address, and ZIP code | ocr |
| symage_900026-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Harmony Home Services | c Employer's name, address, and ZIP code | ocr |
| symage_900027-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Vertex Media Group | c Employer's name, address, and ZIP code | ocr |
| symage_900028-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Infinity Solutions | c Employer's name, address, and ZIP code | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900029-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Clarity Communications Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900030-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Affinity Development Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900031-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Stellar Systems Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900032-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Advocate Solutions LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900033-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Elan Consulting Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900034-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Onyx Properties LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900035-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Arcadia Group LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900036-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Visionary Works LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900037-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | BrightFuture LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900038-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Amber Technologies Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900039-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Global Connect Technologies LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900040-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Nexus Financial Services Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900041-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Pinnacle Growth Strategies | c Employer's name, address, and ZIP code | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900042-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Mastermind Consulting LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900043-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | NextStep Fitness LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900044-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | NextGen Dynamics | c Employer's name, address, and ZIP code | ocr |
| symage_900045-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Bespoke Designs LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900046-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Zenith Education Group | c Employer's name, address, and ZIP code | ocr |
| symage_900047-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | BlueWave Technologies | c Employer's name, address, and ZIP code | ocr |
| symage_900048-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Pure Water Systems | c Employer's name, address, and ZIP code | ocr |
| symage_900049-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | OptiTech Solutions Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900050-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Urban Development Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900051-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Urban Landscape LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900052-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900052-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Blue Horizon Technologies Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900053-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Harvest Moon Design LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900054-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Coastal Insights LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900055-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900055-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Elemental Wellness Center LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900056-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Vibrant Health Solutions Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900057-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Summit Group Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900058-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Harmony Travel Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900059-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | GreenWave Technologies LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900060-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Lighthouse Strategies LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900061-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900061-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Synergize Consulting | c Employer's name, address, and ZIP code | ocr |
| symage_900062-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Vertex Real Estate Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900063-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900063-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Authentic Voice Corp | c Employer's name, address, and ZIP code | ocr |
| symage_900064-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Niche Digital Agency LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900065-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Infinite Loop Solutions | c Employer's name, address, and ZIP code | ocr |
| symage_900066-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Peak Health Solutions LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900067-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Peak Performance Group LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900068-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Edgewater Resources LLC | c Employer's name, address, and ZIP code | ocr |
| symage_900069-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900069-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Prestige Home Improvements Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900070-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |
| symage_900070-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Quantum Dynamics | c Employer's name, address, and ZIP code | ocr |
| symage_900071-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Radiant Energy Solutions Inc. | c Employer's name, address, and ZIP code | ocr |
| symage_900072-irs_w2_single_page_2026-p0 | Rotated | Employer name (`employer.name`) | Solaris Design Co. | c Employer's name, address, and ZIP code | ocr |
| symage_900073-irs_w2_single_page_2026-p0 | Rotated | Box 13 retirement plan (`box_13.retirement_plan`) | False | True | ocr |

## Interpretation

No document-level failures were recorded in this benchmark.
Rotated documents had the lowest field accuracy at 94.17%.
Employer name was the lowest-accuracy field at 75.00%.
These results do not establish production readiness by themselves.
