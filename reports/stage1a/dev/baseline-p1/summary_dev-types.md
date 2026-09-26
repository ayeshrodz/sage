# Stage 1a development summary: `1a-dev-types`

50 requests of 50 types. Development stream: not a registered result.

| System | Correct requests | Correct outputs | Model calls | Tokens (prompt + generated) | CPU s total | CPU per correct | Hits | Hit precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D | 66.0% | 83.2% | 50 | 8,845 + 2,001 | 678.6 | 20.56 s | — | — |
| B | 72.0% | 85.6% | 152 | 22,923 + 5,373 | 1,432.2 | 39.78 s | — | — |
| S | 70.0% | 85.2% | 148 | 22,398 + 5,281 | 1,405.8 | 40.17 s | 2 | 50.0% |
| E | 64.0% | 65.6% | 0 | 0 + 0 | 0.2 | 5.34 ms | — | — |
| E+M | 64.0% | 65.6% | 0 | 0 + 0 | 0.2 | 5.09 ms | 4 | 75.0% |
| S+ | 78.0% | 88.0% | 64 | 9,675 + 2,821 | 690.5 | 17.71 s | 4 | 75.0% |

- S vs B: hits 4.0%, CPU per correct request B ÷ S 1.0×, accuracy -2.0 pts, total CPU ratio 0.982, model calls avoided 4
- E+M vs E: hits 8.0%, CPU per correct request E ÷ E+M 1.0×, accuracy +0.0 pts, total CPU ratio 0.954, model calls avoided 0
- S+ vs B: hits 8.0%, CPU per correct request B ÷ S+ 2.2×, accuracy +6.0 pts, total CPU ratio 0.482, model calls avoided 88
- B's model calls: {'accepted_at_attempt': {1: 12, 2: 5, 3: 2}, 'direct_fallbacks': 31, 'program_calls': 121, 'no_function': 0, 'function_not_fitting': 102, 'mean_program_tokens': 34.12396694214876, 'mean_direct_tokens': 40.12903225806452, 'mean_call_seconds': 2.390525250730259}
- B: git 950720d, model qwen2.5-coder-1.5b-instruct-q4_k_m.gguf, prompts 1a-p1, config {'attempts': 3, 'temperature': 0.7, 'program_tokens': 384, 'direct_tokens': 256}, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4
- D: git f708c82, model qwen2.5-coder-1.5b-instruct-q4_k_m.gguf, prompts 1a-p1, config {'attempts': 3, 'temperature': 0.7, 'program_tokens': 384, 'direct_tokens': 256}, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4
- E: git 5451376, model None, prompts None, config None, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4

Per type (correct requests):

| Type | n | D | B | S | E | E+M | S+ |
|---|---:|---:|---:|---:|---:|---:|---:|
| abbrev_3upper | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| area_code | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| camel_to_snake | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| city_from_address | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| collapse_spaces | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| compact_number | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| company_from_email | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| count_words | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| date_dmy_to_iso | 1 | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| date_iso_to_dmy | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| date_iso_to_long | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| date_long_to_iso | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| email_domain | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| email_from_name | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| email_user | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| file_ext | 1 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| file_stem | 1 | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| first_initial_last | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| first_name | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| hashtags | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| hex_to_rgb | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| initials | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| kg_to_g | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| last_comma_first | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| last_name | 1 | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| mask_card | 1 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| mask_email | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| money_to_number | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| name_titlecase | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| number_to_money | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| path_basename | 1 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| percent | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| phone_digits | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| phone_format | 1 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| phone_intl | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| quarter | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| reverse_words | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| round_int | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| sku_color | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| sku_number | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| slugify | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| snake_to_camel | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| state_from_address | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| time_24_to_12 | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| url_domain | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| url_path | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| username | 1 | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| weekday | 1 | 0.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| year_from_date | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| zip_from_address | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
