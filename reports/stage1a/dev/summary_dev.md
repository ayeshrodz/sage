# Stage 1a development summary: `1a-dev`

100 requests of 30 types. Development stream: not a registered result.

| System | Correct requests | Correct outputs | Model calls | Tokens (prompt + generated) | CPU s total | CPU per correct | Hits | Hit precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D | 78.0% | 87.6% | 100 | 17,132 + 3,510 | 1,230.1 | 15.77 s | — | — |
| B | 71.0% | 83.0% | 443 | 64,111 + 17,283 | 3,839.0 | 54.07 s | — | — |
| S | 77.0% | 87.6% | 333 | 48,542 + 13,727 | 2,961.3 | 38.46 s | 44 | 97.7% |
| E | 66.0% | 66.8% | 0 | 0 + 0 | 0.3 | 5.10 ms | — | — |
| E+M | 66.0% | 66.8% | 0 | 0 + 0 | 0.2 | 2.60 ms | 51 | 98.0% |
| S+ | 81.0% | 90.2% | 209 | 31,142 + 9,949 | 2,076.4 | 25.63 s | 55 | 96.4% |

- S vs B: hits 44.0%, CPU per correct request B ÷ S 1.4×, accuracy +6.0 pts, total CPU ratio 0.771, model calls avoided 110
- E+M vs E: hits 51.0%, CPU per correct request E ÷ E+M 2.0×, accuracy +0.0 pts, total CPU ratio 0.510, model calls avoided 0
- S+ vs B: hits 55.0%, CPU per correct request B ÷ S+ 2.1×, accuracy +10.0 pts, total CPU ratio 0.541, model calls avoided 234
- S vs D: hits 44.0%, CPU per correct request D ÷ S 0.4×, accuracy -1.0 pts, total CPU ratio 2.407, model calls avoided -233
- S+ vs D: hits 55.0%, CPU per correct request D ÷ S+ 0.6×, accuracy +3.0 pts, total CPU ratio 1.688, model calls avoided -109
- B's model calls: {'accepted_at_attempt': {1: 44, 2: 3, 3: 3, 4: 2, 5: 2, 7: 2}, 'direct_fallbacks': 44, 'program_calls': 399, 'no_function': 2, 'function_not_fitting': 341, 'mean_program_tokens': 39.418546365914786, 'mean_direct_tokens': 35.34090909090909, 'mean_call_seconds': 2.1904809910406366}

Fewer program attempts (amendment 1), replayed from B's records: correct requests, CPU per correct request, and for S and S+ the share answered from memory. D ÷ S > 1 means S is cheaper per correct request than D.

| Attempts | B | S | S from memory | D ÷ S | S+ | S+ from memory | D ÷ S+ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 70.0%, 22.96 s | 74.0%, 16.95 s | 37.0% | 0.9× | 78.0%, 9.66 s | 51.0% | 1.6× |
| 2 | 70.0%, 28.70 s | 74.0%, 21.27 s | 40.0% | 0.7× | 78.0%, 13.82 s | 51.0% | 1.1× |
| 3 | 71.0%, 33.68 s | 75.0%, 26.09 s | 40.0% | 0.6× | 79.0%, 17.33 s | 51.0% | 0.9× |
| 4 | 72.0%, 38.24 s | 77.0%, 29.42 s | 41.0% | 0.5× | 81.0%, 19.60 s | 52.0% | 0.8× |
| 5 | 72.0%, 43.62 s | 77.0%, 34.11 s | 41.0% | 0.5× | 81.0%, 23.29 s | 52.0% | 0.7× |
| 6 | 72.0%, 48.65 s | 77.0%, 38.44 s | 41.0% | 0.4× | 81.0%, 26.48 s | 52.0% | 0.6× |
| 7 | 71.0%, 54.06 s | 77.0%, 38.45 s | 44.0% | 0.4× | 81.0%, 25.63 s | 55.0% | 0.6× |
- B: git 4258b3f, model qwen2.5-coder-1.5b-instruct-q4_k_m.gguf, prompts 1a-p1, config {'attempts': 7, 'temperature': 1.0, 'program_tokens': 384, 'direct_tokens': 256}, machine Intel(R) Xeon(R) Processor @ 2.10GHz × 4
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
| file_stem | 12 | 100.0% | 41.7% | 75.0% | 100.0% | 100.0% | 100.0% |
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
| reverse_words | 1 | 0.0% | 100.0% | 100.0% | 0.0% | 0.0% | 100.0% |
| round_int | 4 | 0.0% | 25.0% | 50.0% | 0.0% | 0.0% | 50.0% |
| sku_color | 22 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| snake_to_camel | 3 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 33.3% |
| time_24_to_12 | 7 | 14.3% | 0.0% | 14.3% | 0.0% | 0.0% | 14.3% |
| url_domain | 7 | 28.6% | 28.6% | 28.6% | 0.0% | 0.0% | 28.6% |
| url_path | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| username | 2 | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% |
| zip_from_address | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
