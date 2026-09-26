# Stage 1a development summary: `1a-dev`

100 requests of 30 types. Development stream: not a registered result.

| System | Correct requests | Correct outputs | Model calls | Tokens (prompt + generated) | CPU s total | CPU per correct | Hits | Hit precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D | 78.0% | 87.6% | 100 | 17,132 + 3,510 | 1,230.1 | 15.77 s | — | — |
| B | 68.0% | 80.8% | 257 | 37,996 + 8,304 | 2,293.6 | 33.73 s | — | — |
| S | 73.0% | 85.0% | 197 | 29,193 + 7,038 | 1,846.1 | 25.29 s | 40 | 100.0% |
| E | 66.0% | 66.8% | 0 | 0 + 0 | 0.3 | 5.10 ms | — | — |
| E+M | 66.0% | 66.8% | 0 | 0 + 0 | 0.2 | 2.61 ms | 51 | 98.0% |
| S+ | 78.0% | 87.8% | 128 | 19,229 + 5,111 | 1,285.6 | 16.48 s | 51 | 98.0% |

- S vs B: hits 40.0%, CPU per correct request B ÷ S 1.3×, accuracy +5.0 pts, total CPU ratio 0.805, model calls avoided 60
- E+M vs E: hits 51.0%, CPU per correct request E ÷ E+M 2.0×, accuracy +0.0 pts, total CPU ratio 0.511, model calls avoided 0
- S+ vs B: hits 51.0%, CPU per correct request B ÷ S+ 2.0×, accuracy +10.0 pts, total CPU ratio 0.561, model calls avoided 129
- B's model calls: {'accepted_at_attempt': {1: 44, 2: 5, 3: 1}, 'direct_fallbacks': 50, 'program_calls': 207, 'no_function': 0, 'function_not_fitting': 157, 'mean_program_tokens': 31.32850241545894, 'mean_direct_tokens': 36.38, 'mean_call_seconds': 2.2577006202879395}
- B: git f708c82, model qwen2.5-coder-1.5b-instruct-q4_k_m.gguf, prompts 1a-p1, config {'attempts': 3, 'temperature': 0.7, 'program_tokens': 384, 'direct_tokens': 256}, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4
- D: git f708c82, model qwen2.5-coder-1.5b-instruct-q4_k_m.gguf, prompts 1a-p1, config {'attempts': 3, 'temperature': 0.7, 'program_tokens': 384, 'direct_tokens': 256}, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4
- E: git 5451376, model None, prompts None, config None, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4

Per type (correct requests):

| Type | n | D | B | S | E | E+M | S+ |
|---|---:|---:|---:|---:|---:|---:|---:|
| camel_to_snake | 2 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| city_from_address | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| collapse_spaces | 2 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| compact_number | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| company_from_email | 2 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| count_words | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| date_iso_to_long | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| date_long_to_iso | 2 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| email_user | 8 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| file_ext | 1 | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| file_stem | 12 | 100.0% | 25.0% | 66.7% | 100.0% | 100.0% | 100.0% |
| first_initial_last | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| first_name | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| hashtags | 1 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| initials | 2 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| kg_to_g | 2 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| last_name | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| money_to_number | 5 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| phone_digits | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| phone_format | 3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| phone_intl | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| reverse_words | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| round_int | 4 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| sku_color | 22 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| snake_to_camel | 3 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 33.3% |
| time_24_to_12 | 7 | 14.3% | 14.3% | 14.3% | 0.0% | 0.0% | 14.3% |
| url_domain | 7 | 28.6% | 28.6% | 28.6% | 0.0% | 0.0% | 28.6% |
| url_path | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| username | 2 | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| zip_from_address | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
