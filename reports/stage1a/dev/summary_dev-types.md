# Stage 1a development summary: `1a-dev-types`

50 requests of 50 types. Development stream: not a registered result.

| System | Correct requests | Correct outputs | Model calls | Tokens (prompt + generated) | CPU s total | CPU per correct | Hits | Hit precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D | 66.0% | 83.2% | 50 | 8,845 + 2,001 | 678.6 | 20.56 s | — | — |
| B | 76.0% | 88.0% | 257 | 38,189 + 9,822 | 2,117.3 | 55.72 s | — | — |
| S | 74.0% | 87.6% | 254 | 37,814 + 9,744 | 2,099.9 | 56.76 s | 1 | 0.0% |
| E | 64.0% | 65.6% | 0 | 0 + 0 | 0.2 | 5.34 ms | — | — |
| E+M | 64.0% | 65.6% | 0 | 0 + 0 | 0.2 | 5.09 ms | 4 | 75.0% |
| S+ | 84.0% | 91.6% | 118 | 17,483 + 5,329 | 1,086.2 | 25.86 s | 4 | 75.0% |

- S vs B: hits 2.0%, CPU per correct request B ÷ S 1.0×, accuracy -2.0 pts, total CPU ratio 0.992, model calls avoided 3
- E+M vs E: hits 8.0%, CPU per correct request E ÷ E+M 1.0×, accuracy +0.0 pts, total CPU ratio 0.955, model calls avoided 0
- S+ vs B: hits 8.0%, CPU per correct request B ÷ S+ 2.2×, accuracy +8.0 pts, total CPU ratio 0.513, model calls avoided 139
- S vs D: hits 2.0%, CPU per correct request D ÷ S 0.4×, accuracy +8.0 pts, total CPU ratio 3.095, model calls avoided -204
- S+ vs D: hits 8.0%, CPU per correct request D ÷ S+ 0.8×, accuracy +18.0 pts, total CPU ratio 1.601, model calls avoided -68
- B's model calls: {'accepted_at_attempt': {1: 12, 2: 3, 3: 2, 4: 5, 5: 2, 6: 2, 7: 1}, 'direct_fallbacks': 23, 'program_calls': 234, 'no_function': 1, 'function_not_fitting': 206, 'mean_program_tokens': 37.93589743589744, 'mean_direct_tokens': 41.08695652173913, 'mean_call_seconds': 2.087290439976634}

Fewer program attempts (amendment 1), replayed from B's records: correct requests, CPU per correct request, and for S and S+ the share answered from memory. D ÷ S > 1 means S is cheaper per correct request than D.

| Attempts | B | S | S from memory | D ÷ S | S+ | S+ from memory | D ÷ S+ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 68.0%, 29.45 s | 66.0%, 29.83 s | 2.0% | 0.7× | 76.0%, 11.11 s | 8.0% | 1.9× |
| 2 | 68.0%, 36.02 s | 66.0%, 36.45 s | 2.0% | 0.6× | 76.0%, 14.77 s | 8.0% | 1.4× |
| 3 | 68.0%, 42.66 s | 66.0%, 43.43 s | 2.0% | 0.5× | 76.0%, 18.05 s | 8.0% | 1.1× |
| 4 | 70.0%, 46.96 s | 68.0%, 47.83 s | 2.0% | 0.4× | 78.0%, 20.88 s | 8.0% | 1.0× |
| 5 | 74.0%, 49.20 s | 72.0%, 50.08 s | 2.0% | 0.4× | 82.0%, 22.32 s | 8.0% | 0.9× |
| 6 | 74.0%, 53.28 s | 72.0%, 54.27 s | 2.0% | 0.4× | 82.0%, 24.48 s | 8.0% | 0.8× |
| 7 | 76.0%, 55.71 s | 74.0%, 56.75 s | 2.0% | 0.4× | 84.0%, 25.86 s | 8.0% | 0.8× |
- B: git 20e8230, model qwen2.5-coder-1.5b-instruct-q4_k_m.gguf, prompts 1a-p1, config {'attempts': 7, 'temperature': 1.0, 'program_tokens': 384, 'direct_tokens': 256}, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4
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
| compact_number | 1 | 0.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
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
| path_basename | 1 | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| percent | 1 | 0.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| phone_digits | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| phone_format | 1 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| phone_intl | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| quarter | 1 | 0.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| reverse_words | 1 | 0.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
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
| weekday | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| year_from_date | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| zip_from_address | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
