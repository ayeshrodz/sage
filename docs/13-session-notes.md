# Session notes: how the project unfolded

These notes tell the story of the working session in which SAGE went from a research plan to its first real-workload result. The formal record is in the numbered documents in `docs/`. This is the story around it: what was asked, what was tried, what surprised us and what was dropped. The collaborators were Ayesh and Claude, working in Claude Code.

## How it started

Ayesh had developed a research plan for SAGE with an OpenAI model, and brought the handoff document into a new session with one request: read it, do an independent analysis, and improve the experimental idea, to "develop this together with me". The handoff is kept unchanged as `docs/00-handoff-openai.md`.

The hope behind it, in Ayesh's own objective statement:
- a compact, reusable "cognitive core" that grows its capabilities through memory and executable procedures, while the computation spent per task stays low;
- as a long-term example, about 1 TB of mostly inactive knowledge, with routine active memory under 16 GB;
- in Ayesh's words, the aim is to "bring frontier ai model capability to consumer devices", with AI designed "like a human brain".

## Reframing the idea

Claude's first analysis (`docs/01-independent-analysis.md`) argued that the planned first experiment tested the wrong thing. It compared a hand-written algorithm with a network on graph sizes, which says little about SAGE's actual claim.

The core loop, "solve expensively, store the solution, reuse it cheaply", has a long history: macro-operators, explanation-based learning, Soar and DreamCoder. It also has a known failure, the *utility problem*: every stored skill makes the search wider and choosing between skills harder, until the system gets slower. A toy pilot showed exactly that:
- with the right library, every target was solved, against 3% with no library;
- with 100 irrelevant extra entries and no guide, only 20% were;
- at 10,000 entries, just scoring the entries took 99.9% of the work.

The proposal was to test library economics first and leave the neural interpreter for later. Ayesh agreed, and set a few things:
- the domain: typed relational worlds;
- the local hardware question postponed ("let's just forget this part for now");
- a small language model allowed as a helper: "we can use a smaller tiny ai model to improve our model as a start".

## Experiment 0: four synthetic stages

Every stage was pre-registered: criteria and thresholds were written down before any code or data existed, and the hidden test data was generated and run once. Ayesh's approvals were short ("Yes, go with stage 0d").

- **0a.** A given library cut search work at least 90-fold. The early runs had their own surprises, both fixed before the registered run: random targets kept collapsing into short programs, and the tie-breaking rule quietly favoured library entries.
- **0b.** Learning a library from scratch recovered real procedures, but stalled without a guide. One criterion failed and one passed.
- **0c.** A refactoring learner with a learned guide solved 62% of unseen compositional tasks. But the guide cost more per decision than it saved, and learning took about a thousand tasks to repay.
- **0d.** A memory of verified programs made recognized recurring tasks about 1,000 times cheaper, and more accurate: 85–91% correct against 37–68%. About 30% of recurrences were still missed, mostly because the first stored solution was over-specific. A "consolidating" memory meant to fix that was tried on development data and dropped.

## The turning point: is this realistic?

After 0d, Ayesh asked whether this was "a realistic model that can revolutionize the existing AI deployment".

Claude's answer was no as a replacement for large models, because every test had relied on four conditions most AI work lacks:
- a cheap, exact checker;
- a clean instruction set;
- repetition;
- small scale.

But the answer was yes as a layer: solve a recurring, checkable task once, store the verified procedure, and rerun it locally for almost nothing. The suggestion was to test that claim directly on a real workload. Ayesh's reply: "Set up the real workload stage with the small LLM".

## Stage 1a: a real workload

The stage was set up like this:
- **Requests:** everyday data cleaning by example, across 50 kinds of transformation ("Mary Chen" → "M.C."). Each request gives three examples and asks for five more answers.
- **Model:** a 1.5-billion-parameter coding model (Qwen2.5-Coder-1.5B-Instruct, 4-bit) on a CPU.
- **Baseline without a model:** a classical synthesizer.
- **Comparison:** a memory of verified functions in front of the model, against calling the model every time.

Four pass marks were registered before any code existed:
- at least half the requests answered from memory;
- at least twice as cheap per correct answer;
- no more than 2 points of accuracy lost;
- under 5% extra cost when nothing recurs.

## Getting a model into a locked-down cloud machine

The cloud environment's network policy blocked Hugging Face, so the model couldn't be downloaded. Everything else was built and tested anyway:
- a stand-in "model" (the classical synthesizer) dry-ran the whole pipeline;
- a tiny random-weight model, built locally as a test fixture, exercised the real llama.cpp code path.

Given recent security incidents, Ayesh didn't want to give the environment blanket access to Hugging Face. The first idea was to download the model by hand and upload it through the repository. GitHub refuses files over 100 MB, so a small tool was written to split the file into checksummed 45 MB parts on a separate branch.

Ayesh then found Hugging Face's one-line installer and download command. Claude suggested installing the same tool from PyPI instead of piping a script into the shell. It also pointed out that the command named the *base* model in full precision, not the instruction-tuned 4-bit file the stage needed.

In the end Ayesh allowed the Hugging Face domains temporarily, after first failing to find the setting in the mobile app. The download took about 20 seconds, the checksum matched Hugging Face's listing, and the split-and-upload tool was never needed.

## Tuning: harder and easier than expected

- **Easier:** the model ran faster than estimated, at 1–5 seconds per call on four cores.
- **Harder:** the small model wrote a function that fitted the examples for only 19 of the 50 types. It failed even on trivial ones whose direct answers it got right, often reaching for strange regular expressions.
- **Prompt rewording didn't help.** Four prompt variants made no difference: a clearer layout, stating the rule first, a worked example, and retries showing the model its mistakes. The retries made things slightly worse.
- **Surprise: sampling luck, not wording.** Across the variants, 29 types got a working function at least once but only 2 got one every time. The fix was more attempts. The rule for choosing how many was written down before the numbers were computed, and it picked 7 attempts at a higher sampling temperature.
- **Second surprise: the model answering directly beat the model writing functions.** So "memory against asking directly" was added as a comparison before the registered run.
- **The written expectation:** memory would probably miss the cost target, and would cost more than asking directly.

## The registered run, and a pleasant surprise

Midway through the run, Ayesh asked: "do we see any positive progress?" When it finished, all four pass marks were met:
- 74% of requests were answered from memory;
- 2.9 times cheaper per correct answer than calling the model to write functions every time;
- 3.3 points more accurate;
- no extra cost when nothing recurs.

Against the model answering directly, the memory systems were 92–93% correct against 71%, and 1.4–2.2 times cheaper per correct answer.

The written expectation had been wrong. The development stream had fewer repeats, and more of the types the model can't write functions for. The model's direct mistakes were small slips that a verified function never makes:
- misordered words;
- "OscaR";
- "Than" for "Ethan";
- a middle name kept by mistake.

Functions that had already fitted five or more requests were right on all 150 answers they gave.

The caveats were recorded just as plainly:
- the savings depend on requests recurring;
- without recurrence, memory costs more than asking directly;
- the real bottleneck is writing a correct procedure in the first place, not reusing it;
- fewer attempts per request would have been more economical.

## What Ayesh wants next

Ayesh asked where to go next, and whether to work on a local machine with Claude Code or with OpenAI Codex and a frontier model.

The recommendation was stage 1b: a stronger "teacher" model writes functions when memory misses, and the small model and memory serve everything else. It would run on Ayesh's own machine, where consumer-CPU costs and energy can actually be measured. Since the repository holds the whole protocol, the coding tool matters less than the setup.

Ayesh set the project up on a fresh Ubuntu machine:
- all tests passed;
- the model ran about as fast as it had in the cloud;
- the CPU's energy counters were available.

One decision is still open: which teacher. It could be a frontier API, a local 7B model, or both.
