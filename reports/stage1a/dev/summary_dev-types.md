# Stage 1a development summary: `1a-dev-types`

50 requests of 50 types. Development stream: not a registered result.

| System | Correct requests | Correct outputs | Model calls | Tokens (prompt + generated) | CPU s total | CPU per correct | Hits | Hit precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E | 64.0% | 65.6% | 0 | 0 + 0 | 0.2 | 5.34 ms | — | — |
| E+M | 64.0% | 65.6% | 0 | 0 + 0 | 0.2 | 5.08 ms | 4 | 75.0% |

- E+M vs E: hits 8.0%, CPU per correct request E ÷ E+M 1.1×, accuracy +0.0 pts, total CPU ratio 0.952, model calls avoided 0
- E: git 5451376, model None, prompts None, config None, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4

Per type (correct requests):

| Type | n | E | E+M |
|---|---:|---:|---:|
| abbrev_3upper | 1 | 100.0% | 100.0% |
| area_code | 1 | 100.0% | 100.0% |
| camel_to_snake | 1 | 0.0% | 0.0% |
| city_from_address | 1 | 100.0% | 100.0% |
| collapse_spaces | 1 | 100.0% | 100.0% |
| compact_number | 1 | 0.0% | 0.0% |
| company_from_email | 1 | 0.0% | 0.0% |
| count_words | 1 | 0.0% | 0.0% |
| date_dmy_to_iso | 1 | 100.0% | 100.0% |
| date_iso_to_dmy | 1 | 100.0% | 100.0% |
| date_iso_to_long | 1 | 0.0% | 0.0% |
| date_long_to_iso | 1 | 0.0% | 0.0% |
| email_domain | 1 | 100.0% | 100.0% |
| email_from_name | 1 | 100.0% | 100.0% |
| email_user | 1 | 100.0% | 100.0% |
| file_ext | 1 | 0.0% | 0.0% |
| file_stem | 1 | 100.0% | 100.0% |
| first_initial_last | 1 | 100.0% | 100.0% |
| first_name | 1 | 100.0% | 100.0% |
| hashtags | 1 | 0.0% | 0.0% |
| hex_to_rgb | 1 | 0.0% | 0.0% |
| initials | 1 | 100.0% | 100.0% |
| kg_to_g | 1 | 100.0% | 100.0% |
| last_comma_first | 1 | 100.0% | 100.0% |
| last_name | 1 | 100.0% | 100.0% |
| mask_card | 1 | 100.0% | 100.0% |
| mask_email | 1 | 100.0% | 100.0% |
| money_to_number | 1 | 100.0% | 100.0% |
| name_titlecase | 1 | 100.0% | 100.0% |
| number_to_money | 1 | 100.0% | 100.0% |
| path_basename | 1 | 100.0% | 100.0% |
| percent | 1 | 0.0% | 0.0% |
| phone_digits | 1 | 100.0% | 100.0% |
| phone_format | 1 | 100.0% | 100.0% |
| phone_intl | 1 | 100.0% | 100.0% |
| quarter | 1 | 0.0% | 0.0% |
| reverse_words | 1 | 0.0% | 0.0% |
| round_int | 1 | 0.0% | 0.0% |
| sku_color | 1 | 100.0% | 100.0% |
| sku_number | 1 | 100.0% | 100.0% |
| slugify | 1 | 100.0% | 100.0% |
| snake_to_camel | 1 | 0.0% | 0.0% |
| state_from_address | 1 | 100.0% | 100.0% |
| time_24_to_12 | 1 | 0.0% | 0.0% |
| url_domain | 1 | 0.0% | 0.0% |
| url_path | 1 | 0.0% | 0.0% |
| username | 1 | 100.0% | 100.0% |
| weekday | 1 | 0.0% | 0.0% |
| year_from_date | 1 | 100.0% | 100.0% |
| zip_from_address | 1 | 100.0% | 100.0% |
