# Stage 1a development summary: `1a-dev`

100 requests of 30 types. Development stream: not a registered result.

| System | Correct requests | Correct outputs | Model calls | Tokens (prompt + generated) | CPU s total | CPU per correct | Hits | Hit precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E | 66.0% | 66.8% | 0 | 0 + 0 | 0.3 | 5.10 ms | — | — |
| E+M | 66.0% | 66.8% | 0 | 0 + 0 | 0.2 | 2.60 ms | 51 | 98.0% |

- E+M vs E: hits 51.0%, CPU per correct request E ÷ E+M 2.0×, accuracy +0.0 pts, total CPU ratio 0.510, model calls avoided 0
- E: git 5451376, model None, prompts None, config None, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4

Per type (correct requests):

| Type | n | E | E+M |
|---|---:|---:|---:|
| camel_to_snake | 2 | 0.0% | 0.0% |
| city_from_address | 1 | 100.0% | 100.0% |
| collapse_spaces | 2 | 100.0% | 100.0% |
| compact_number | 2 | 0.0% | 0.0% |
| company_from_email | 2 | 0.0% | 0.0% |
| count_words | 1 | 0.0% | 0.0% |
| date_iso_to_long | 1 | 0.0% | 0.0% |
| date_long_to_iso | 2 | 0.0% | 0.0% |
| email_user | 8 | 100.0% | 100.0% |
| file_ext | 1 | 100.0% | 100.0% |
| file_stem | 12 | 100.0% | 100.0% |
| first_initial_last | 1 | 100.0% | 100.0% |
| first_name | 1 | 100.0% | 100.0% |
| hashtags | 1 | 0.0% | 0.0% |
| initials | 2 | 100.0% | 100.0% |
| kg_to_g | 2 | 100.0% | 100.0% |
| last_name | 1 | 100.0% | 100.0% |
| money_to_number | 5 | 100.0% | 100.0% |
| phone_digits | 1 | 100.0% | 100.0% |
| phone_format | 3 | 100.0% | 100.0% |
| phone_intl | 1 | 100.0% | 100.0% |
| reverse_words | 1 | 0.0% | 0.0% |
| round_int | 4 | 0.0% | 0.0% |
| sku_color | 22 | 100.0% | 100.0% |
| snake_to_camel | 3 | 0.0% | 0.0% |
| time_24_to_12 | 7 | 0.0% | 0.0% |
| url_domain | 7 | 0.0% | 0.0% |
| url_path | 1 | 0.0% | 0.0% |
| username | 2 | 100.0% | 100.0% |
| zip_from_address | 1 | 100.0% | 100.0% |
