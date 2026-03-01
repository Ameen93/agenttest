# AgentTest Improvement Ideas

From real-world usage testing the Bidzani chatbot (streaming AI chat endpoint).

## 1. Streaming Response Support

**Problem:** The HTTP adapter buffers the full response body, which works but loses visibility into streaming endpoints. The raw body for AI SDK streaming contains protocol markers like `0:"text"` mixed with actual content. Assertions like `contains` and `regex` match against the raw stream data (which does include the text), but it's fragile — you're matching against a transport protocol, not the logical content.

**Suggestion:** Add an `adapter.stream_mode` option (e.g., `sse`, `ndjson`, `ai-sdk-ui`) that:
- Buffers the stream but parses it into logical text content before running assertions
- For AI SDK UI streams: extract just the text parts from the `0:"..."` lines
- For SSE: concatenate `data:` fields
- This would make `contains`/`regex` assertions much more reliable for streaming APIs

## 2. Response Body Capture in Reports

**Problem:** When a test fails, the JSON report shows the assertion failure but not the actual response body. Debugging requires re-running the test or adding snapshot tracking. The `snapshot_changed` feature exists but the snapshot files don't store the raw body.

**Suggestion:** Include `response_body` (or a truncated version, first 2000 chars) in the test results in the JSON report. This makes debugging much faster — you can see exactly what the API returned without re-running.

## 3. Flaky Test Awareness for AI Endpoints

**Problem:** AI responses are non-deterministic. A test might pass 4/5 times. The `--reruns` flag helps, but it retries the entire test. For AI testing, what you often want is "pass if it passes N out of M attempts" (e.g., 2 out of 3).

**Suggestion:** Add a per-test `flaky_threshold` option:
```yaml
- id: some_test
  flaky_threshold: 2/3  # Pass if 2 out of 3 attempts pass
```

## 4. Negative Timing Assertions

**Problem:** Some tool-using AI tests are slow (10-15s) because the AI makes a tool call mid-response. There's `max_latency_ms` for upper bounds, but no `min_latency_ms`. For a test expecting tool usage, a fast response (<2s) might indicate the AI skipped the tool and hallucinated instead.

**Suggestion:** Add `min_latency_ms` assertion type — if the response comes back suspiciously fast for a test that should trigger tool use, flag it.

## 5. Multi-Turn Conversation Support (Stateful Tests)

**Problem:** Testing multi-turn conversations requires manually constructing the message history in the test YAML. The assistant messages have to be hand-written, which means the test doesn't reflect how the AI actually responds. This makes some tests (like qualification flow) unreliable because the AI sees fake assistant messages it didn't write.

**Suggestion:** Add a `conversation` test type that chains multiple turns:
```yaml
- id: multi_turn_flow
  type: conversation
  turns:
    - user: "I want a Toyota Hilux in Joburg"
      assertions:
        - type: contains
          value: "budget"
    - user: "Around R600k"
      assertions:
        - type: regex
          pattern: "(?i)dealer"
    - user: "Yes, send it"
      assertions:
        - type: contains
          value: "QUALIFICATION_COMPLETE"
```

Each turn sends the user message + the actual AI responses from previous turns (not hand-crafted ones). This would be the single biggest improvement for testing conversational AI.

## 6. LLM-as-Judge Assertion Type

**Problem:** Deterministic assertions (contains, regex) can only test surface-level patterns. You can't test "did the AI give helpful advice?" or "did it acknowledge the user's budget constraint?" without brittle keyword matching.

**Suggestion:** Add an `llm_judge` assertion type that uses a small/fast model to evaluate:
```yaml
assertions:
  - type: llm_judge
    prompt: "Did the assistant search for vehicles and present real price data?"
    model: claude-haiku  # fast, cheap judge
    pass_threshold: 0.8
```

This would unlock semantic quality testing for AI agents.

## 7. Tag-Based Test Ordering

**Problem:** All tests run sequentially in YAML order. For large suites against AI endpoints (which are slow), you might want smoke tests first, then detailed tests.

**Suggestion:** Add `--tags-order smoke,happy,tool_use,safety` to control execution order by tag priority. If a smoke test fails, you can `--fail-fast` to skip the rest.

## 8. Cost Tracking

**Problem:** Each test against an AI endpoint costs API credits. A full suite of 18 tests costs ~18 API calls. There's no visibility into the cumulative cost.

**Suggestion:** If the response includes token usage headers (like `x-usage-input-tokens`), capture and report them in the summary. Even an estimate based on response size would be helpful.
